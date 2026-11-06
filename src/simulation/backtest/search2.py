"""Stage-2 search on the conservative table (tweet count lagged 2 h, then lag-corrected). TRAIN only; top rules re-scored on TEST
and on the zero-lag / 3 h-lag tables for robustness."""
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.simulation.backtest.data import CACHE                   # noqa: E402
from src.simulation.backtest.sim import Strat, evaluate, prep    # noqa: E402


def load(name):
    evs = prep(pd.read_pickle(CACHE / name))
    cut = len(evs) * 2 // 3
    return evs[:cut], evs[cut:]


if __name__ == "__main__":
    train, test = load("table_lag2_stale6_corr.pkl")
    rows = []
    for w, k, edge, minp, start, adds in itertools.product((0.5, 1.0), (2, 3, 5), (0.02, 0.04, 0.08), (0.10, 0.20), (0, 96, 120), (0, 2)):
        S = Strat(w=w, top_k=k, min_edge=edge, min_p=minp, start_after_h=start, max_adds=adds)
        rows.append({"w": w, "k": k, "edge": edge, "minp": minp, "start": start, "adds": adds, **evaluate(train, S)})
    df = pd.DataFrame(rows)
    df["score"] = df["mean"] - 0.5 * df["std"]
    df.to_csv(CACHE / "search_stage2.csv", index=False)
    cols = ["w", "k", "edge", "minp", "start", "adds", "mean", "median", "std", "worst", "win_rate", "bad_weeks", "buys"]
    top = df.sort_values("score", ascending=False).head(10)
    print(top[cols].round(2).to_string(index=False))
    print("\nre-scored on TEST (lag2 corr) / TEST lag0 / TEST lag3 corr:")
    alt = {n: load(n)[1] for n in ("table.pkl", "table_lag3_stale6_corr.pkl")}
    for r in top.itertuples():
        S = Strat(w=r.w, top_k=r.k, min_edge=r.edge, min_p=r.minp, start_after_h=r.start, max_adds=r.adds)
        t = evaluate(test, S)
        a0, a3 = evaluate(alt["table.pkl"], S), evaluate(alt["table_lag3_stale6_corr.pkl"], S)
        print(f"w={r.w} k={r.k} edge={r.edge} minp={r.minp} start={r.start} adds={r.adds} | test mean {t['mean']:+.2f} med {t['median']:+.2f} worst {t['worst']:+.1f} buys {t['buys']} | lag0 {a0['mean']:+.2f} | lag3 {a3['mean']:+.2f}")
