"""
Run the paper trader.

LIVE (never stops by itself; Ctrl-C to stop, run again to resume):
    python -m src.simulation.paper_trader --run-name paper1

REPLAY a finished weekly market through the same engine in seconds (for testing/validation):
    python -m src.simulation.paper_trader --run-name replay1 --replay elon-musk-of-tweets-october-16-october-23-2026
"""
import argparse
import logging
import os
import signal
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from .feeds import LiveFeed, ReplayFeed
from .procutil import AlreadyRunning, RunLock, write_exit_status
from .runner import PaperTrader, configure_logging
from .strategy import Rules


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-name", default="paper_elon", help="results go to <runs-dir>/<run-name>/")
    ap.add_argument("--runs-dir", default=str(ROOT / "src" / "simulation" / "runs"))
    ap.add_argument("--slug", default=None, help="event slug to start on (default: the one in src/constants.py)")
    ap.add_argument("--bankroll", type=float, default=30.0)
    ap.add_argument("--stake", type=float, default=1.0, help="USDC per buy, fee included (min 1.0)")
    ap.add_argument("--min-pred", type=float, default=8.0, help="our probability must be at least this, in %%")
    ap.add_argument("--min-mkt", type=float, default=3.0, help="market ask must be at least this, in %%")
    ap.add_argument("--min-edge", type=float, default=1.0, help="our probability must exceed the ask by more than this, in percentage points")
    ap.add_argument("--sell-below", type=float, default=4.0, help="sell when our probability drops below this, in %%")
    ap.add_argument("--no-bid-sell", action="store_true", help="disable the 'sell when market bid > our probability' rule")
    ap.add_argument("--buy-every", type=int, default=60, help="minutes between buys")
    ap.add_argument("--sell-every", type=int, default=10, help="minutes between ticks / sell checks")
    ap.add_argument("--model-refresh", type=int, default=60, help="minutes between ensemble re-runs")
    ap.add_argument("--pred-source", choices=["calibrated", "ensemble"], default="calibrated",
                    help="calibrated = ensemble total + recalibrated bucket shape (backtested); ensemble = its native probabilities")
    ap.add_argument("--b", type=float, default=1.15, help="multiplier on the ensemble's remaining-tweets forecast")
    ap.add_argument("--start-after-days", type=float, default=2.0, help="don't buy until this many days after a market opens")
    ap.add_argument("--max-slippage", type=float, default=1.0, help="reject a buy if the average fill is worse than the best ask by this many points")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-auto-roll", action="store_true", help="stop trading when the current market ends instead of moving to the next")
    ap.add_argument("--chart-every", type=int, default=1, help="rewrite charts every N ticks")
    ap.add_argument("--once", action="store_true", help="run a single live tick and exit (smoke test)")
    ap.add_argument("--fresh", action="store_true", help="start over: delete the run's saved state first")
    rp = ap.add_argument_group("replay")
    rp.add_argument("--replay", metavar="SLUG", help="replay a finished market instead of trading live")
    rp.add_argument("--half-spread", type=float, default=0.5, help="replay: assumed distance from mid to bid/ask, in points")
    rp.add_argument("--fee-rate", type=float, default=0.05, help="replay: taker fee rate (0 to disable fees)")
    return ap


def _main(argv=None):
    a = build_parser().parse_args(argv)
    run_dir = os.path.join(a.runs_dir, a.run_name)
    if a.fresh and os.path.isdir(run_dir):
        for f in os.listdir(run_dir):
            if f.endswith((".json", ".csv", ".png", ".txt", ".log", ".lock")):
                os.remove(os.path.join(run_dir, f))
    configure_logging(run_dir, mirror_console=not a.replay)
    import json, subprocess, datetime as _dt
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = ""
    with open(os.path.join(run_dir, "config_history.jsonl"), "a") as f:          # one line per (re)start, never overwritten
        f.write(json.dumps({"started_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "argv": sys.argv[1:],
                            "args": vars(a), "git_commit": commit}) + "\n")
    if a.stake < 1.0:
        raise SystemExit("--stake must be at least 1.0 (Polymarket's minimum market order)")
    try:
        lock = RunLock(os.path.join(run_dir, "run.lock")).acquire()     # held for the life of the process (B14)
    except AlreadyRunning as ex:
        raise SystemExit(str(ex))
    rules = Rules(stake=a.stake, min_pred=a.min_pred / 100, min_mkt=a.min_mkt / 100, min_edge=a.min_edge / 100,
                  sell_below=a.sell_below / 100, sell_if_bid_above_pred=not a.no_bid_sell)
    try:
        if a.replay:
            feed = ReplayFeed(half_spread=a.half_spread / 100, fee_rate=a.fee_rate, step_min=a.sell_every)
            trader = PaperTrader(feed, rules, run_dir, a.bankroll, a.pred_source, a.buy_every, a.sell_every, a.model_refresh,
                                 a.seed, a.b, False, a.start_after_days, a.max_slippage / 100, chart_every=36)
            st = trader.run_replay(a.replay)
            print(open(os.path.join(run_dir, "summary.txt")).read())
            return 0
        feed = LiveFeed()
        trader = PaperTrader(feed, rules, run_dir, a.bankroll, a.pred_source, a.buy_every, a.sell_every, a.model_refresh,
                             a.seed, a.b, not a.no_auto_roll, a.start_after_days, a.max_slippage / 100, a.chart_every, verbose=True)
        from constants import EVENT_HASH
        slug = a.slug or trader.account.state.get("current_slug") or EVENT_HASH
        trader.event = feed.load_event(slug)
        trader.events[slug] = trader.event
        trader.account.state["current_slug"] = slug
        trader.account.state["rules"] = rules.as_dict()
        trader.account.save()
        def _on_signal(signum, _frame):
            logging.getLogger("paper_trader").warning("received signal %s - stopping after the current tick", signal.Signals(signum).name)
            write_exit_status(run_dir, f"signal {signal.Signals(signum).name}", 0, pending=True)
            trader.stop()
        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)
        if a.once:
            trader.tick(pd.Timestamp.now(tz="UTC"))
            return 0
        trader.run_live()
        return 0
    finally:
        lock.release()


def main(argv=None):
    """Outermost boundary: whatever kills the process leaves a traceback in the log and exit_status.json (B02)."""
    import logging
    import traceback
    a, _ = build_parser().parse_known_args(argv)
    run_dir = os.path.join(a.runs_dir, a.run_name)
    try:
        code = _main(argv)
        write_exit_status(run_dir, "clean exit", int(code or 0))
        return code
    except SystemExit as ex:
        write_exit_status(run_dir, "SystemExit", ex.code if isinstance(ex.code, int) else 1, detail=str(ex.code))
        raise
    except KeyboardInterrupt:
        logging.getLogger("paper_trader").error("interrupted (KeyboardInterrupt)")
        write_exit_status(run_dir, "KeyboardInterrupt", 130)
        return 130
    except BaseException as ex:
        logging.getLogger("paper_trader").exception("FATAL: paper trader is exiting on an uncaught exception")
        write_exit_status(run_dir, "uncaught exception", 1, error=repr(ex), traceback=traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
