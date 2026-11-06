"""
Walk-forward calibration of the tweet-count models, using ONLY the tweet history (no market prices):
for every 7-day window (a start every day) and several lead times, forecast the 20-wide bucket distribution of the final
count from tweets before that moment, and score the probability given to the true bucket (log loss).

    python -m src.simulation.backtest.eval_model
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.simulation.paper_trader.light_model import LightModel, LightParams, load_times   # noqa: E402
from src.simulation.paper_trader.model import gamma_bucket_probs                          # noqa: E402

CSV = str(ROOT / "src" / "data" / "elonmusk_reformatted.csv")
LEADS_DAYS = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
RANGES = [(i, i + 19) for i in range(0, 1200, 20)]


def windows(times, first="2024-09-01", last_end=None):
    """7-day windows starting 12:00 ET on every day (like the real markets)."""
    last_end = pd.Timestamp(last_end) if last_end else pd.Timestamp(times.max()).floor("D") - pd.Timedelta(days=0)
    starts = pd.date_range(first, last_end - pd.Timedelta(days=7), freq="D") + pd.Timedelta(hours=12)
    return [(s, s + pd.Timedelta(days=7)) for s in starts if s + pd.Timedelta(days=7) <= pd.Timestamp(times.max())]


def count_between(times, a, b):
    return int(np.searchsorted(times, np.datetime64(b), "right") - np.searchsorted(times, np.datetime64(a), "left"))


def score(times, params, wins, leads=LEADS_DAYS):
    """Mean log loss of the true 20-bucket, per lead, for LightModel(params)."""
    out = {l: [] for l in leads}
    m = LightModel(times, params)
    for s, e in wins:
        final = count_between(times, s, e)
        idx = final // 20
        for l in leads:
            now = s + pd.Timedelta(days=l)
            m.fit(now)
            so = count_between(times, s, now)
            if final < so:
                continue
            p = m.bucket_probs(RANGES, s, now, e, so)
            out[l].append(-np.log(max(p[idx], 1e-6)))
    return {l: float(np.mean(v)) for l, v in out.items()}


def score_baseline(times, wins, b=1.15, leads=LEADS_DAYS):
    """The previous replay stand-in: trailing 7-day mean rate x b into a Gamma shape (what the old model reduces to)."""
    out = {l: [] for l in leads}
    for s, e in wins:
        final = count_between(times, s, e)
        idx = final // 20
        for l in leads:
            now = s + pd.Timedelta(days=l)
            so = count_between(times, s, now)
            rate = max(count_between(times, now.floor("D") - pd.Timedelta(days=7), now.floor("D")) / 7.0, 1.0)
            left = (e - now) / pd.Timedelta(days=1)
            p = gamma_bucket_probs(RANGES, so, rate, left, b)
            out[l].append(-np.log(max(p[idx], 1e-6)))
    return {l: float(np.mean(v)) for l, v in out.items()}


if __name__ == "__main__":
    times = load_times(CSV)
    wins = windows(times)
    cut = len(wins) * 2 // 3
    train, test = wins[:cut], wins[cut:]
    print(f"{len(wins)} windows; train {train[0][0]:%Y-%m-%d}..{train[-1][0]:%Y-%m-%d} ({len(train)}), test {test[0][0]:%Y-%m-%d}..{test[-1][0]:%Y-%m-%d} ({len(test)})")
    base = score_baseline(times, test)
    print("old model (7d rate x1.15, Gamma)   test logloss by lead:", {k: round(v, 3) for k, v in base.items()}, "mean", round(np.mean(list(base.values())), 3))
    grid = list(itertools.product((7, 14, 21), (14, 28), (4, 8), (10.0, 20.0, 50.0), (2.0, 4.0, 8.0)))
    res = []
    for ld, hd, dw, a, phi in grid:
        pr = LightParams(level_days=ld, hod_days=hd, dow_weeks=dw, prior_a=a, phi=phi)
        sc = score(times, pr, train[::3])
        res.append((np.mean(list(sc.values())), pr))
    res.sort(key=lambda x: x[0])
    for v, pr in res[:5]:
        print("train", round(v, 3), pr)
    best = res[0][1]
    sc = score(times, best, test)
    print("BEST on TEST by lead:", {k: round(v, 3) for k, v in sc.items()}, "mean", round(np.mean(list(sc.values())), 3))
    print("default params on TEST:", round(np.mean(list(score(times, LightParams(), test).values())), 3))
