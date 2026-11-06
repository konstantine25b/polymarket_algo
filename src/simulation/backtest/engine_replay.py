"""
End-to-end backtest through the REAL engine (PaperTrader + ReplayFeed + the same CLI presets as live), market by market:
synthetic book = historical hourly mid +/- 1pt, 5% taker fees, $40 bankroll, $1 stakes, hourly ticks.

    python -m src.simulation.backtest.engine_replay [first_n_from_the_end]
Output: cache/engine_replay.csv (one row per variant x market) and a summary table.
"""
import json
import sys
import io
import contextlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from src.simulation.backtest.data import CACHE, list_weekly_slugs   # noqa: E402
from src.simulation.paper_trader.__main__ import main               # noqa: E402

VARIANTS = {
    "light (hold)": ["--strategy", "light"],
    "light + sell when bid>prob+5pt": ["--strategy", "light", "--bid-sell-margin", "5"],
    "legacy (old rules, old-style forecast)": ["--strategy", "legacy"],
}
COMMON = ["--bankroll", "40", "--sell-every", "60", "--buy-every", "60", "--half-spread", "1.0", "--fee-rate", "0.05"]


def run(slug, variant, args, runs_dir):
    name = f"{variant.split()[0]}_{abs(hash(variant)) % 10000}_{slug[-30:]}"
    argv = ["--run-name", name, "--runs-dir", str(runs_dir), "--replay", slug] + COMMON + args
    with contextlib.redirect_stdout(io.StringIO()):
        main(argv)
    st = json.load(open(Path(runs_dir) / name / "state.json"))
    return {"variant": variant, "slug": slug, "pnl": st["cash"] - 40.0 + sum(p["cost_usd"] for p in st["positions"].values()),
            "buys": st["n_buys"], "sells": st["n_sells"], "fees": st["fees_paid"], "cash": st["cash"]}


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 33
    runs_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else CACHE / "engine_runs"
    slugs = [s for s in list_weekly_slugs() if (CACHE / f"{s}.json").exists()][-n:]
    rows = []
    for i, s in enumerate(slugs):
        for v, a in VARIANTS.items():
            try:
                rows.append(run(s, v, a, runs_dir))
            except Exception as ex:
                print("FAILED", v, s, repr(ex)[:150], flush=True)
        print(f"{i + 1}/{len(slugs)} {s}", flush=True)
        pd.DataFrame(rows).to_csv(CACHE / "engine_replay.csv", index=False)
    df = pd.DataFrame(rows)
    g = df.groupby("variant").pnl
    out = pd.DataFrame({"markets": g.size(), "mean": g.mean(), "median": g.median(), "worst": g.min(), "best": g.max(),
                        "weeks>0": g.apply(lambda x: (x > 0).mean()), "lose>50%": g.apply(lambda x: (x < -20).mean()),
                        "buys": df.groupby("variant").buys.sum(), "sells": df.groupby("variant").sells.sum()})
    print(out.round(2).to_string())
