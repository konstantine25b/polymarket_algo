"""
Builds the backtest table: for every cached weekly market and every hour of its life
    market mid price per bucket (last observation <= t, NaN if older than 6 h), light-model probability per bucket,
    tweets counted so far (from the tweet CSV, causal), hours left.
Saved to cache/table.pkl so strategy experiments run in seconds.
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.simulation.backtest.data import CACHE, load_all                                   # noqa: E402
from src.simulation.paper_trader.light_model import LightModel, LightParams, load_times   # noqa: E402

CSV = str(ROOT / "src" / "data" / "elonmusk_reformatted.csv")
ET = "US/Eastern"


def to_et_naive(ts):
    return pd.Timestamp(ts).tz_convert(ET).tz_localize(None)


def build(params=None, stale_h=6, count_lag_h=0, lag_correct=False):
    times = load_times(CSV)
    model = LightModel(times, params or LightParams())
    rows = []
    for ev in load_all():
        start_utc, end_utc = pd.Timestamp(ev["start"]), pd.Timestamp(ev["end"])
        s_et, e_et = to_et_naive(start_utc), to_et_naive(end_utc)
        if np.datetime64(e_et) > times.max():
            continue                                             # no tweet data for the whole window yet
        ranges = [(b["lo"], b["hi"]) for b in ev["buckets"]]
        titles = [b["title"] for b in ev["buckets"]]
        series = [pd.Series([p for _, p in b["prices"]], index=pd.to_datetime([t for t, _ in b["prices"]], unit="s", utc=True)) for b in ev["buckets"]]
        winner = titles.index(ev["winner"])
        final = int(np.searchsorted(times, np.datetime64(e_et), "right") - np.searchsorted(times, np.datetime64(s_et), "left"))
        grid = pd.date_range(start_utc.ceil("h"), end_utc - pd.Timedelta(hours=1), freq="h")
        for t in grid:
            now_et = to_et_naive(t)
            mids = []
            for s in series:
                prev = s[s.index <= t]
                mids.append(prev.iloc[-1] if len(prev) and (t - prev.index[-1]) <= pd.Timedelta(hours=stale_h) else np.nan)
            so = max(0, int(np.searchsorted(times, np.datetime64(now_et - pd.Timedelta(hours=count_lag_h)), "right") - np.searchsorted(times, np.datetime64(s_et), "left")))
            model.fit(now_et)
            if lag_correct and count_lag_h:
                so += int(round(model.exposure(now_et - pd.Timedelta(hours=count_lag_h), now_et)))   # add what the profile expects in the unseen hours
            pm = model.bucket_probs(ranges, s_et, now_et, e_et, so)
            rows.append({"slug": ev["slug"], "t": t, "hours_into": (t - start_utc) / pd.Timedelta(hours=1),
                         "hours_left": (end_utc - t) / pd.Timedelta(hours=1), "so_far": so, "final": final, "winner": winner,
                         "fee_rate": ev["buckets"][0]["fee_rate"], "mid": np.array(mids, float), "model": pm, "lo": np.array([r[0] for r in ranges]),
                         "hi": np.array([r[1] for r in ranges])})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    lag = int(sys.argv[1]) if len(sys.argv) > 1 else 0          # simulate a tweet count that lags by this many hours
    stale = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    corr = len(sys.argv) > 3 and sys.argv[3] == "correct"
    df = build(stale_h=stale, count_lag_h=lag, lag_correct=corr)
    df.to_pickle(CACHE / ("table.pkl" if (lag, stale, corr) == (0, 6, False) else f"table_lag{lag}_stale{stale}{'_corr' if corr else ''}.pkl"))
    print(len(df), "rows,", df.slug.nunique(), "markets")
