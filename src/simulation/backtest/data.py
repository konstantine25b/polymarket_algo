"""
Historical weekly Elon-tweet markets for backtesting: bucket structure, final winner and hourly price history of
every bucket's YES token (Polymarket CLOB prices-history, fidelity 60 min). Cached on disk (cache/ is git-ignored).

    python -m src.simulation.backtest.data          # download / refresh the cache
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from ..paper_trader.feeds import CLOB, GAMMA, SLUG_PREFIX, _event_from_gamma, http_get, resolution_from_gamma

CACHE = Path(__file__).resolve().parent / "cache"


def list_weekly_slugs():
    """Closed ~7-day weekly markets (the 2-day weekend ones are a different product and are skipped)."""
    seen = {}
    for q in ("elon musk # tweets", "elon musk tweets"):
        for page in (1, 2, 3):
            try:
                d = http_get(f"{GAMMA}/public-search", {"q": q, "limit_per_type": 50, "events_status": "closed", "page": page})
            except Exception:
                break
            for e in d.get("events", []):
                if e["slug"].startswith(SLUG_PREFIX) and e.get("startTime"):
                    days = (pd.Timestamp(e["endDate"]) - pd.Timestamp(e["startTime"])) / pd.Timedelta(days=1)
                    if 6 <= days <= 8:
                        seen[e["slug"]] = pd.Timestamp(e["endDate"])
    return [s for s, _ in sorted(seen.items(), key=lambda x: x[1])]


def fetch_event(slug: str, fidelity: int = 60):
    path = CACHE / f"{slug}.json"
    if path.exists():
        return json.load(open(path))
    raw = http_get(f"{GAMMA}/events", {"slug": slug})[0]
    res = resolution_from_gamma(raw)
    if res is None:
        return None
    ev = _event_from_gamma(raw, only_open=False)

    def hist(b):
        h = http_get(f"{CLOB}/prices-history", {"market": b.token, "startTs": int(ev.start.timestamp()) - 3600,
                                                "endTs": int(ev.end.timestamp()), "fidelity": fidelity})
        return [(x["t"], x["p"]) for x in h.get("history", [])]
    with ThreadPoolExecutor(8) as ex:
        hists = list(ex.map(hist, ev.buckets))
    out = {"slug": slug, "start": ev.start.isoformat(), "end": ev.end.isoformat(), "winner": next(t for t, w in res.items() if w),
           "buckets": [{"title": b.title, "lo": b.lo, "hi": b.hi, "fee_rate": b.fees.rate, "prices": h} for b, h in zip(ev.buckets, hists)]}
    CACHE.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(path, "w"))
    return out


def load_all():
    return [e for e in (fetch_event(s) for s in list_weekly_slugs()) if e]


if __name__ == "__main__":
    evs = load_all()
    print(f"{len(evs)} weekly markets cached in {CACHE}")
    for e in evs[-5:]:
        print(e["slug"], "winner", e["winner"], "buckets", len(e["buckets"]), "pts", len(e["buckets"][0]["prices"]))
