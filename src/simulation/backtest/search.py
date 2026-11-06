"""Stage-1 strategy search on TRAIN markets only; the top candidates are then scored once on the held-out TEST markets."""
import itertools
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.simulation.backtest.data import CACHE   # noqa: E402
from src.simulation.backtest.sim import Strat, evaluate, prep   # noqa: E402


def split():
    evs = prep(pd.read_pickle(CACHE / "table.pkl"))
    cut = len(evs) * 2 // 3
    return evs[:cut], evs[cut:]


if __name__ == "__main__":
    train, test = split()
    rows = []
    for w, k, edge, minp, adds in itertools.product((0.0, 0.5, 1.0), (1, 2, 3, 4, 5, 99), (0.01, 0.02, 0.04, 0.06), (0.05, 0.10, 0.15), (0, 2)):
        S = Strat(w=w, top_k=k, min_edge=edge, min_p=minp, max_adds=adds)
        r = evaluate(train, S)
        rows.append({**{"w": w, "k": k, "edge": edge, "minp": minp, "adds": adds}, **r})
    df = pd.DataFrame(rows)
    df["score"] = df["mean"] - 0.5 * df["std"]
    df.to_csv(CACHE / "search_stage1.csv", index=False)
    cols = ["w", "k", "edge", "minp", "adds", "mean", "median", "std", "worst", "win_rate", "bad_weeks", "buys"]
    print("TOP 12 by mean - 0.5*std (train)")
    print(df.sort_values("score", ascending=False).head(12)[cols].round(2).to_string(index=False))
    print("TOP 8 by mean (train)")
    print(df.sort_values("mean", ascending=False).head(8)[cols].round(2).to_string(index=False))
