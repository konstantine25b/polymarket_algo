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
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests

from .checkpoint import backup_tweet_csv
from .fills import FeeSchedule
from .model import parse_range
from .strategy import Quote

log = logging.getLogger("paper_trader.feeds")
ROOT = Path(__file__).resolve().parents[3]
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
SLUG_PREFIX = "elon-musk-of-tweets"
ET = "US/Eastern"


class StartupCheckError(RuntimeError):
    """A live-run prerequisite (browser, page scrape) is missing; the message says how to fix it."""


def http_get(url, params=None, tries=4, timeout=25, deadline=None, headers=None):
    """GET + json with retries. `deadline` (seconds, whole call) bounds the total time so one slow endpoint cannot stall a tick."""
    last, t0 = None, time.monotonic()
    for i in range(tries):
        left = None if deadline is None else deadline - (time.monotonic() - t0)
        if left is not None and left <= 0.5:
            last = (last or "") + " (time budget used up)"
            break
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout if left is None else max(1.0, min(timeout, left)))
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}"
            if r.status_code in (400, 404):          # permanent (e.g. a delisted bucket's book): retrying only slows every tick down
                break
            if r.status_code == 429:                 # rate limited: honour Retry-After instead of hammering
                try:
                    time.sleep(min(float(r.headers.get("Retry-After", 0)), 10.0))
                except (TypeError, ValueError):
                    pass
        except Exception as e:  # network hiccup: retry with backoff
            last = repr(e)
        if i < tries - 1:
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET {url} failed: {last}")


def run_bounded(cmd, timeout, **kw):
    """Run a command in its own process group and return a CompletedProcess. On timeout the WHOLE group (python + the Chromium it
    spawned) is killed, so a hung scrape cannot stall the tick or leave orphan browsers behind; the partial output rides on the error."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True, **kw)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, err = proc.communicate()
        raise subprocess.TimeoutExpired(cmd, timeout, output=out, stderr=err)
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


@dataclass
class Bucket:
    title: str
    lo: int
    hi: int
    token: str
    fees: FeeSchedule
    closed: bool = False          # market closed / not accepting orders / no order book: expected to have no book


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

    def __init__(self, tweet_refresh_timeout=420, model_timeout=1500, backup_dir=None, book_budget=45, scrape_timeout=90,
                 meta_every_min=30, refresh_tries=3, refresh_budget=330):
        self.backup_dir = backup_dir
        self.refresh_tries, self.refresh_budget = refresh_tries, refresh_budget     # per-refresh retry count / total seconds (small when refreshing every tick)
        self.tweet_refresh_timeout = tweet_refresh_timeout
        self.model_timeout = model_timeout
        self.book_budget = book_budget              # seconds for ALL order-book requests of one tick
        self.scrape_timeout = scrape_timeout        # seconds for the page scrape (browser launch + load + read)
        self.meta_every = pd.Timedelta(minutes=meta_every_min)
        self._no_book = {}                          # token -> title: Polymarket answered 404 "no orderbook" (closed/delisted bucket)
        self._meta_at = {}                          # slug -> UTC time of the last bucket-metadata refresh
        self.book_report = {}                       # last quotes() outcome: expected / ok / failed / closed
        self.count_error = None                     # why the last tweet_count() returned None (None = it worked)
        self.timings = {}                           # seconds spent in each step of the last tick

    def load_event(self, slug: str) -> Event:
        data = http_get(f"{GAMMA}/events", {"slug": slug})
        if not data:
            raise RuntimeError(f"event not found: {slug}")
        self._meta_at[slug] = pd.Timestamp.now(tz="UTC")
        return _event_from_gamma(data[0], only_open=True)

    def sync_markets(self, event: Event, force=False):
        """Re-read the buckets' current token ids and open/closed state from gamma (the event object is built once at start-up, so
        a token that changes or a bucket that closes mid-week would otherwise 404 on every tick). Never raises."""
        now = pd.Timestamp.now(tz="UTC")
        last = self._meta_at.get(event.slug)
        if not force and last is not None and now - last < self.meta_every:
            return
        self._meta_at[event.slug] = now
        try:
            data = http_get(f"{GAMMA}/events", {"slug": event.slug}, tries=2, timeout=10, deadline=20)
            markets = {m.get("groupItemTitle"): m for m in data[0]["markets"]}
        except Exception as ex:
            log.warning("could not refresh bucket metadata (keeping the previous one): %s", ex)
            return
        for b in event.buckets:
            m = markets.get(b.title)
            if m is None:
                continue
            try:
                token = json.loads(m["clobTokenIds"])[0]
            except Exception:
                token = b.token
            if token != b.token:
                log.warning("bucket %s: token id changed - using the new one", b.title)
                self._no_book.pop(b.token, None)
                b.token = token
            closed = bool(m.get("closed")) or not m.get("enableOrderBook", True) or not m.get("acceptingOrders", True)
            if closed != b.closed:
                log.info("bucket %s is now %s", b.title, "CLOSED (no order book expected)" if closed else "open")
            b.closed = closed
            if not closed and b.token in self._no_book:
                self._no_book.pop(b.token)            # it has a market again: try its book

    def quotes(self, event: Event, now=None) -> Dict[str, Quote]:
        """Order books of every bucket that should have one, within `book_budget` seconds in total. Closed buckets / known-404
        tokens are skipped (and reported separately, not as failures); transient failures get a second, slower pass."""
        self.sync_markets(event)
        t0 = time.monotonic()
        live = [b for b in event.buckets if not b.closed and b.token not in self._no_book]
        closed = [b.title for b in event.buckets if b.closed or b.token in self._no_book]
        out: Dict[str, Quote] = {}
        failed: Dict[str, str] = {}

        def one(b: Bucket):
            left = self.book_budget - (time.monotonic() - t0)
            try:
                book = http_get(f"{CLOB}/book", {"token_id": b.token}, tries=3, timeout=10, deadline=max(left, 1.0))
                bids = [(float(x["price"]), float(x["size"])) for x in book.get("bids", [])]
                asks = [(float(x["price"]), float(x["size"])) for x in book.get("asks", [])]
                return b, Quote(bids, asks), None
            except Exception as ex:
                return b, None, str(ex)

        def collect(buckets, workers):
            pool = ThreadPoolExecutor(workers)
            futs = [pool.submit(one, b) for b in buckets]
            done, pending = wait(futs, timeout=max(self.book_budget - (time.monotonic() - t0), 1.0))
            pool.shutdown(wait=False, cancel_futures=True)           # never block the tick on a hung request
            for f in done:
                b, q, err = f.result()
                if q is not None:
                    out[b.title] = q
                    failed.pop(b.title, None)
                else:
                    failed[b.title] = err
            for f in pending:
                failed.setdefault(buckets[futs.index(f)].title, "timed out")

        collect(live, 6)
        retry = [b for b in live if b.title in failed and "HTTP 404" not in failed[b.title] and "HTTP 400" not in failed[b.title]]
        if retry and time.monotonic() - t0 < self.book_budget - 5:
            time.sleep(1.0)
            collect(retry, 2)                                         # slower second pass: rate limits / transient errors
        for b in live:
            err = failed.get(b.title)
            if err and ("HTTP 404" in err or "HTTP 400" in err):     # permanent: the bucket has no book (closed / delisted)
                self._no_book[b.token] = b.title
                closed.append(b.title)
                failed.pop(b.title)
                log.warning("bucket %s has no order book (%s) - treated as closed, will not be requested again until its market changes", b.title, err[-40:])
        for t, err in failed.items():
            log.warning("book fetch failed for %s: %s", t, err)
        self.book_report = {"expected": len(live) - sum(1 for b in live if b.token in self._no_book), "ok": len(out),
                            "failed": sorted(failed), "closed": closed, "seconds": round(time.monotonic() - t0, 1)}
        self.timings["order_books"] = self.book_report["seconds"]
        return out

    XTRACKER_STATS = "https://www.xtracker.io/api/users"

    def xtracker_sync(self, now=None) -> dict:
        """When did XTracker itself last sync with X, and did that sync report an error? A cheap HTTP call (no browser) that tells a
        quiet account apart from a stalled XTracker pipeline. Never raises: {'ok': False, 'error': ...} if the check itself fails."""
        t0 = time.monotonic()
        try:
            users = http_get(self.XTRACKER_STATS, {"stats": "true", "platform": "X"}, tries=2, timeout=10, deadline=20,
                             headers={"User-Agent": "Mozilla/5.0"})
            u = next(x for x in users if x.get("handle") == "elonmusk")
            last = pd.Timestamp(u["lastSync"])
            now = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz="UTC")
            return {"ok": True, "last_sync": last, "age_min": (now - last) / pd.Timedelta(minutes=1), "error": u.get("lastSyncError")}
        except Exception as ex:
            return {"ok": False, "error": f"XTracker sync status unreadable: {ex!r}"[:300]}
        finally:
            self.timings["xtracker_sync"] = round(time.monotonic() - t0, 1)

    def tweet_count(self, event: Event, now=None) -> Optional[int]:
        """Polymarket's own count for the event (this is what the market resolves on). None = unreadable; the reason is
        in self.count_error and is logged here (a missing browser is logged as an ERROR on every attempt)."""
        t0 = time.monotonic()
        self.count_error = None
        try:
            p = run_bounded([sys.executable, "-m", "src.xpath_scraper.NumberGetter", "--url", event.url], self.scrape_timeout, cwd=ROOT)
            m = re.search(r"Tweet count: (-?\d+)", p.stdout)
            n = int(m.group(1)) if m else -1
            if n >= 0:
                return n
            if p.returncode == 3 or "BROWSER_ERROR" in p.stdout:
                self.count_error = (re.search(r"BROWSER_ERROR: (.*)", p.stdout) or [None, "browser unavailable"])[1]
                log.error("tweet count NOT READ - the browser is unusable: %s", self.count_error)
            else:
                tail = " | ".join(l for l in (p.stderr or "").splitlines() if "ERROR" in l or "Error" in l)[-300:] or (p.stderr or p.stdout)[-300:]
                self.count_error = f"page scrape failed (rc={p.returncode}): {tail}"
                log.warning("tweet count not read: %s", self.count_error)
        except subprocess.TimeoutExpired:
            self.count_error = f"page scrape timed out after {self.scrape_timeout}s (process group killed)"
            log.warning("tweet count not read: %s", self.count_error)
        except Exception as ex:
            self.count_error = repr(ex)
            log.warning("tweet count failed: %s", ex)
        finally:
            self.timings["page_scrape"] = round(time.monotonic() - t0, 1)
        return None

    def preflight(self, event: Event, attempts=2):
        """Start-up check for a LIVE run: Chromium is installed and NumberGetter can read the event page's count.
        Raises StartupCheckError with the fix in the message. Without this the bot would quietly fall back to the CSV count
        (which the light strategy refuses to trade on) and sit idle."""
        try:
            import playwright.sync_api  # noqa: F401
        except ImportError:
            raise StartupCheckError("The Python package 'playwright' is not installed. Run: pip install -r requirements-light.txt")
        for i in range(attempts):
            n = self.tweet_count(event)
            if n is not None:
                log.info("start-up check OK: Chromium works and the Polymarket page shows %d tweets", n)
                return n
            if self.count_error and ("not installed" in self.count_error or "failed to launch" in self.count_error):
                break                                           # an installation problem: retrying cannot help
            time.sleep(3)
        reason = self.count_error or "unknown"
        hint = ("Install the browser:  python -m playwright install chromium   (Linux: add --with-deps)"
                if "hromium" in reason or "browser" in reason.lower() else
                "The browser works but the count could not be read from the page: check the network and that the event URL is right")
        raise StartupCheckError(f"START-UP CHECK FAILED - cannot read Polymarket's tweet count from {event.url}\n  reason: {reason}\n  fix   : {hint}\n"
                                "  (the light strategy only trades on that count; refusing to start and sit idle. Use --skip-preflight to override.)")

    csv_path = str(ROOT / "src" / "data" / "elonmusk_reformatted.csv")

    def local_count(self, event: Event, now=None):
        """Tweets in our own CSV inside the market window, and the timestamp of the newest tweet."""
        t = pd.to_datetime(pd.read_csv(self.csv_path, usecols=["created_at"]).created_at,
                           format="%Y:%m:%d:%H:%M:%S", errors="coerce").dropna()
        lo = event.start.tz_convert(ET).tz_localize(None)
        hi = (now or pd.Timestamp.now(tz="UTC")).tz_convert(ET).tz_localize(None)
        return int(((t >= lo) & (t <= hi)).sum()), (t.max() if len(t) else None)

    @staticmethod
    def _refresh_error_text(stdout: str, stderr: str) -> str:
        """The exact cause of a failed refresh. TweetCSVGetter prints a REFRESH_ERROR line listing every attempt's error (e.g.
        'XTracker answered HTTP 403 Forbidden ...'); without it, fall back to the ERROR lines of the log, then the raw tail."""
        m = re.search(r"REFRESH_ERROR (\{.*\})", stdout or "")
        if m:
            try:
                d = json.loads(m.group(1))
                return " | ".join(d.get("attempts") or []) or d.get("error", "")
            except Exception:
                pass
        errs = [l.split(" - ", 3)[-1] for l in (stderr or "").splitlines() if " - ERROR - " in l]
        if errs:
            return " | ".join(errs)[-1200:]
        return ((stderr or "") + (stdout or ""))[-800:] or "no output"

    def refresh_tweet_data(self) -> dict:
        """Download the XTracker export and merge it into the CSV (src.xpath_scraper.TweetCSVGetter).
        Success needs exit code 0 AND the pipeline's own REFRESH_RESULT line - exit 0 alone is not proof (B04/B05)."""
        t0 = time.time()
        info = {"ok": False, "new_tweets": None, "seconds": 0.0}
        try:
            p = subprocess.run([sys.executable, "-m", "src.xpath_scraper.TweetCSVGetter", "--tries", str(self.refresh_tries),
                                "--max-seconds", str(self.refresh_budget)], cwd=ROOT,
                               capture_output=True, text=True, timeout=self.tweet_refresh_timeout, start_new_session=True)
            m = re.search(r"REFRESH_RESULT (\{.*\})", p.stdout)
            if p.returncode != 0:
                info["error"] = f"exit code {p.returncode}: " + self._refresh_error_text(p.stdout, p.stderr)
            elif not m:
                info["error"] = "refresh exited 0 but reported no REFRESH_RESULT (treated as failure): " + self._refresh_error_text(p.stdout, p.stderr)
            else:
                res = json.loads(m.group(1))
                info.update(ok=True, new_tweets=res.get("new_rows"), rows=res.get("total_rows"), newest=res.get("newest"),
                            sha256=res.get("sha256"))
        except subprocess.TimeoutExpired as ex:
            out, err = (x.decode(errors="replace") if isinstance(x, bytes) else (x or "") for x in (ex.stdout, ex.stderr))
            info["error"] = f"timed out after {self.tweet_refresh_timeout}s: " + self._refresh_error_text(out, err)
        except Exception as ex:
            info["error"] = repr(ex)
        info["seconds"] = round(time.time() - t0, 1)
        if info["ok"] and self.backup_dir:
            try:
                backup_tweet_csv(self.csv_path, self.backup_dir, info.get("sha256"))
            except Exception as ex:
                log.error("tweet dataset backup failed: %r", ex)
        if info["ok"]:
            log.info("tweet data refreshed from XTracker: %s new tweets merged, %s rows, newest %s (%.0fs)", info["new_tweets"],
                     info.get("rows"), info.get("newest"), info["seconds"])
        else:
            log.error("tweet data refresh FAILED: %s", info.get("error"))
        return info

    def forecast(self, event: Event, now: pd.Timestamp, out_dir: str, seed: int = 42) -> Optional[dict]:
        """Refresh tweet data, then run the ensemble in a subprocess on an immutable snapshot of the CSV.
        Any failure (refresh, worker, bad output) returns None - a forecast is never built on data we know is stale."""
        refresh = self.refresh_tweet_data()
        if not refresh["ok"]:
            log.error("forecast aborted: tweet data could not be refreshed, so training data would be stale")
            return None
        start, end = event.window_et()
        out = os.path.join(out_dir, "forecast.json")
        stamp = now.strftime("%Y%m%d_%H%M")
        attempt = f"{stamp}_{os.getpid()}_{int(time.time())}"
        log_out = os.path.join(out_dir, "model_logs", f"model_{stamp}.log")
        err_out = os.path.join(out_dir, "model_logs", f"attempt_{attempt}.stderr")
        os.makedirs(os.path.dirname(err_out), exist_ok=True)
        snap = os.path.join(out_dir, "model_logs", f"data_{attempt}.csv")
        try:
            shutil.copyfile(self.csv_path, snap)                 # the worker reads this snapshot, not the live file
            if os.path.exists(out):
                os.remove(out)                                   # never re-read a previous run's result
            p = subprocess.run([sys.executable, "-m", "src.simulation.paper_trader.model_worker", "--start", start,
                                "--end", end, "--now", now.tz_convert(ET).strftime("%Y-%m-%d %H:%M:%S"),
                                "--out", out, "--seed", str(seed), "--log-out", log_out, "--data-path", snap,
                                "--slug", event.slug], cwd=ROOT, capture_output=True, text=True, timeout=self.model_timeout)
            with open(err_out, "w") as f:                        # keep the worker's full stderr on success AND failure
                f.write(f"returncode={p.returncode}\n{p.stderr}")
            if p.returncode != 0:
                log.error("model worker failed (rc=%s, full stderr in %s): %s", p.returncode, err_out, p.stderr[-800:])
                return None
            with open(out) as f:
                fc = json.load(f)
            fc["data_sha256"] = refresh.get("sha256")
            fc["data_newest"] = refresh.get("newest")
            return fc
        except Exception as ex:
            log.error("model worker error: %r", ex)
            return None
        finally:
            if os.path.exists(snap):
                os.remove(snap)

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
