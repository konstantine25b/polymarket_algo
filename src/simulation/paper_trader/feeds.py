"""
Market data sources for the paper trader.

LiveFeed   : real Polymarket data - gamma API (event/markets/resolution), CLOB order books, the
             event page's tweet count, and the ensemble (run in a separate process) for forecasts.
ReplayFeed : replays a *finished* weekly market from Polymarket's 10-minute price history with a
             synthetic book (mid +/- half spread) and a cheap trailing-average forecast, so the
             exact same engine can be run through a whole past week in seconds.
"""
import json
import logging
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests

from .fills import FeeSchedule
from .model import parse_range
from .strategy import Quote

log = logging.getLogger("paper_trader.feeds")
ROOT = Path(__file__).resolve().parents[3]
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
SLUG_PREFIX = "elon-musk-of-tweets"
ET = "US/Eastern"


def http_get(url, params=None, tries=4, timeout=25):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}"
        except Exception as e:  # network hiccup: retry with backoff
            last = repr(e)
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET {url} failed: {last}")


@dataclass
class Bucket:
    title: str
    lo: int
    hi: int
    token: str
    fees: FeeSchedule


@dataclass
class Event:
    slug: str
    title: str
    start: pd.Timestamp        # UTC
    end: pd.Timestamp          # UTC
    buckets: List[Bucket] = field(default_factory=list)

    @property
    def url(self):
        return f"https://polymarket.com/event/{self.slug}"

    @property
    def ranges(self):
        return [(b.lo, b.hi) for b in self.buckets]

    def window_et(self):
        f = lambda t: t.tz_convert(ET).strftime("%Y-%m-%d %H:%M:%S")
        return f(self.start), f(self.end)

    def days_left(self, now: pd.Timestamp) -> float:
        return max((self.end - now) / pd.Timedelta(days=1), 0.0)


def _event_from_gamma(e: dict, only_open: bool) -> Event:
    buckets = []
    for m in e["markets"]:
        if only_open and (m.get("closed") or not m.get("enableOrderBook", True) or not m.get("acceptingOrders", True)):
            continue
        try:
            token = json.loads(m["clobTokenIds"])[0]
            lo, hi = parse_range(m["groupItemTitle"])
        except Exception:
            continue
        buckets.append(Bucket(m["groupItemTitle"], lo, hi, token, FeeSchedule.from_market(m)))
    buckets.sort(key=lambda b: b.lo)
    start = pd.Timestamp(e.get("startTime") or e["startDate"])
    return Event(e["slug"], e["title"], start, pd.Timestamp(e["endDate"]), buckets)


def resolution_from_gamma(e: dict) -> Optional[Dict[str, bool]]:
    """{bucket title: won?} once EVERY market is closed with a 0/1 outcome, else None."""
    out = {}
    for m in e["markets"]:
        try:
            yes = float(json.loads(m["outcomePrices"])[0])
        except Exception:
            return None
        if not m.get("closed") or yes not in (0.0, 1.0):
            return None
        out[m["groupItemTitle"]] = yes == 1.0
    return out if sum(out.values()) == 1 else None


class LiveFeed:
    mode = "live"

    def __init__(self, tweet_refresh_timeout=240, model_timeout=1500):
        self.tweet_refresh_timeout = tweet_refresh_timeout
        self.model_timeout = model_timeout

    def load_event(self, slug: str) -> Event:
        data = http_get(f"{GAMMA}/events", {"slug": slug})
        if not data:
            raise RuntimeError(f"event not found: {slug}")
        return _event_from_gamma(data[0], only_open=True)

    def quotes(self, event: Event, now=None) -> Dict[str, Quote]:
        def one(b: Bucket):
            try:
                book = http_get(f"{CLOB}/book", {"token_id": b.token}, tries=3)
                bids = [(float(x["price"]), float(x["size"])) for x in book.get("bids", [])]
                asks = [(float(x["price"]), float(x["size"])) for x in book.get("asks", [])]
                return b.title, Quote(bids, asks)
            except Exception as ex:
                log.warning("book fetch failed for %s: %s", b.title, ex)
                return b.title, None
        with ThreadPoolExecutor(8) as ex:
            return {t: q for t, q in ex.map(one, event.buckets) if q is not None}

    def tweet_count(self, event: Event, now=None) -> Optional[int]:
        """Polymarket's own count for the event (this is what the market resolves on)."""
        try:
            p = subprocess.run([sys.executable, "-m", "src.xpath_scraper.NumberGetter", "--url", event.url],
                               capture_output=True, text=True, cwd=ROOT, timeout=120)
            m = re.search(r"Tweet count: (-?\d+)", p.stdout)
            n = int(m.group(1)) if m else -1
            return n if n >= 0 else None
        except Exception as ex:
            log.warning("tweet count failed: %s", ex)
            return None

    csv_path = str(ROOT / "src" / "data" / "elonmusk_reformatted.csv")

    def local_count(self, event: Event, now=None):
        """Tweets in our own CSV inside the market window, and the timestamp of the newest tweet."""
        t = pd.to_datetime(pd.read_csv(self.csv_path, usecols=["created_at"]).created_at,
                           format="%Y:%m:%d:%H:%M:%S", errors="coerce").dropna()
        lo = event.start.tz_convert(ET).tz_localize(None)
        hi = (now or pd.Timestamp.now(tz="UTC")).tz_convert(ET).tz_localize(None)
        return int(((t >= lo) & (t <= hi)).sum()), (t.max() if len(t) else None)

    def refresh_tweet_data(self) -> dict:
        """Download the XTracker export and merge it into the CSV (src.xpath_scraper.TweetCSVGetter)."""
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, "-m", "src.xpath_scraper.TweetCSVGetter"], cwd=ROOT,
                               capture_output=True, text=True, timeout=self.tweet_refresh_timeout)
            m = re.search(r"Found (\d+) new entries", p.stdout + p.stderr)
            info = {"ok": p.returncode == 0, "new_tweets": int(m.group(1)) if m else None, "seconds": round(time.time() - t0, 1)}
            if p.returncode != 0:
                info["error"] = (p.stderr or p.stdout)[-300:]
        except Exception as ex:
            info = {"ok": False, "new_tweets": None, "seconds": round(time.time() - t0, 1), "error": repr(ex)}
        if info["ok"]:
            log.info("tweet data refreshed from XTracker: %s new tweets merged (%.0fs)", info["new_tweets"], info["seconds"])
        else:
            log.warning("tweet data refresh FAILED (continuing with the data we have): %s", info.get("error"))
        return info

    def forecast(self, event: Event, now: pd.Timestamp, out_dir: str, seed: int = 42) -> Optional[dict]:
        """Refresh tweet data, then run the ensemble in a subprocess. Returns its forecast dict."""
        self.refresh_tweet_data()
        start, end = event.window_et()
        out = os.path.join(out_dir, "forecast.json")
        stamp = now.strftime("%Y%m%d_%H%M")
        log_out = os.path.join(out_dir, "model_logs", f"model_{stamp}.log")
        try:
            p = subprocess.run([sys.executable, "-m", "src.simulation.paper_trader.model_worker", "--start", start,
                                "--end", end, "--now", now.tz_convert(ET).strftime("%Y-%m-%d %H:%M:%S"),
                                "--out", out, "--seed", str(seed), "--log-out", log_out], cwd=ROOT, capture_output=True, text=True,
                               timeout=self.model_timeout)
            if p.returncode != 0:
                log.error("model worker failed: %s", p.stderr[-800:])
                return None
            with open(out) as f:
                return json.load(f)
        except Exception as ex:
            log.error("model worker error: %s", ex)
            return None

    def resolution(self, event: Event) -> Optional[Dict[str, bool]]:
        data = http_get(f"{GAMMA}/events", {"slug": event.slug})
        return resolution_from_gamma(data[0]) if data else None

    def next_event(self, after_end: pd.Timestamp, now: pd.Timestamp) -> Optional[str]:
        """Slug of the next ~7-day weekly market that ends after `after_end`."""
        data = http_get(f"{GAMMA}/public-search", {"q": "elon musk # tweets", "limit_per_type": 40,
                                                   "events_status": "active"})
        best = None
        for e in data.get("events", []):
            if not e["slug"].startswith(SLUG_PREFIX) or not e.get("startTime"):
                continue
            end, start = pd.Timestamp(e["endDate"]), pd.Timestamp(e["startTime"])
            if 6 <= (end - start) / pd.Timedelta(days=1) <= 8 and end > after_end + pd.Timedelta(hours=1) and end > now:
                if best is None or end < best[0]:
                    best = (end, e["slug"])
        return best[1] if best else None


class ReplayFeed:
    """Replays a finished weekly market. `half_spread` is the assumed distance from mid to bid/ask."""
    mode = "replay"

    def __init__(self, half_spread=0.005, fee_rate=0.05, csv_path=None, start_after_days=2.0, step_min=10):
        self.half = half_spread
        self.fee_rate = fee_rate
        self.csv = csv_path or str(ROOT / "src" / "data" / "elonmusk_reformatted.csv")
        self.start_after_days = start_after_days
        self.step_min = step_min
        self._hist = {}
        self._tweets = None
        self._raw = None

    def load_event(self, slug: str) -> Event:
        data = http_get(f"{GAMMA}/events", {"slug": slug})
        if not data:
            raise RuntimeError(f"event not found: {slug}")
        self._raw = data[0]
        ev = _event_from_gamma(self._raw, only_open=False)
        for b in ev.buckets:                       # replay with the CLI fee rate, not today's schedule
            b.fees = FeeSchedule(self.fee_rate, 1.0)

        def hist(b):
            h = http_get(f"{CLOB}/prices-history", {"market": b.token, "startTs": int(ev.start.timestamp()) - 3600,
                                                    "endTs": int(ev.end.timestamp()), "fidelity": self.step_min})
            return b.title, h.get("history", [])
        with ThreadPoolExecutor(8) as ex:
            self._hist = dict(ex.map(hist, ev.buckets))
        t = pd.read_csv(self.csv)
        self._tweets = np.sort(pd.to_datetime(t.created_at, format="%Y:%m:%d:%H:%M:%S").values)
        return ev

    def grid(self, event: Event):
        t0 = event.start + pd.Timedelta(days=self.start_after_days)
        return list(pd.date_range(t0, event.end - pd.Timedelta(minutes=self.step_min), freq=f"{self.step_min}min"))

    def quotes(self, event: Event, now: pd.Timestamp) -> Dict[str, Quote]:
        out, ts = {}, now.timestamp()
        for b in event.buckets:
            h = self._hist.get(b.title) or []
            prev = [x for x in h if x["t"] <= ts]
            if not prev or ts - prev[-1]["t"] > 3 * 3600:
                continue
            mid = prev[-1]["p"]
            if mid < 0.002:
                continue
            ask, bid = min(mid + self.half, 0.999), max(mid - self.half, 0.001)
            out[b.title] = Quote([(bid, 1e9)], [(ask, 1e9)])
        return out

    def tweet_count(self, event: Event, now: pd.Timestamp) -> int:
        f = lambda t: np.datetime64(t.tz_convert(ET).tz_localize(None))
        return int(np.searchsorted(self._tweets, f(now), "right") - np.searchsorted(self._tweets, f(event.start), "left"))

    def local_count(self, event: Event, now: pd.Timestamp):
        return self.tweet_count(event, now), None

    def forecast(self, event: Event, now: pd.Timestamp, out_dir: str = "", seed: int = 42) -> dict:
        """Cheap causal stand-in for the ensemble: trailing 7-complete-day average rate."""
        et_now = np.datetime64(now.tz_convert(ET).tz_localize(None))
        day0 = et_now.astype("datetime64[D]")
        lo, hi = day0 - np.timedelta64(7, "D"), day0
        n = int(np.searchsorted(self._tweets, hi.astype("datetime64[ns]"), "left") - np.searchsorted(self._tweets, lo.astype("datetime64[ns]"), "left"))
        rate = max(n / 7.0, 1.0)
        so_far, left = self.tweet_count(event, now), event.days_left(now)
        return {"total_predicted": so_far + rate * left, "current_tweets": so_far, "time_remaining_days": left, "frames": None}

    def resolution(self, event: Event):
        return resolution_from_gamma(self._raw)
