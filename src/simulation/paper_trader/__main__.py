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
import shutil
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
    ap.add_argument("--min-pred", type=float, default=None, help="our probability must be at least this, in %%")
    ap.add_argument("--min-mkt", type=float, default=None, help="market ask must be at least this, in %%")
    ap.add_argument("--min-edge", type=float, default=None, help="our probability must exceed the ask by more than this, in percentage points")
    ap.add_argument("--sell-below", type=float, default=None, help="sell when our probability drops below this, in %%")
    ap.add_argument("--strategy", choices=["light", "legacy"], default="light",
                    help="light = backtested preset (lightweight model, top-2 buckets, no averaging down, hold to settlement); "
                         "legacy = the original rules + Prophet/TimesFM ensemble. Any explicit flag overrides the preset.")
    ap.add_argument("--top-k", type=int, default=None, help="only buy buckets ranked in the model's top K (0 = any)")
    ap.add_argument("--max-adds", type=int, default=None, help="extra buys allowed in a bucket already held (0 = never average down, -1 = unlimited)")
    ap.add_argument("--pick-random", action="store_true", help="draw the bucket at random (weight = edge) instead of taking the best net edge")
    ap.add_argument("--max-data-age-h", type=float, default=36.0, help="light model: no new buys if the newest tweet in our history is older than this")
    ap.add_argument("--count-lag-h", type=float, default=0.0, help="light model: hours the tweet count lags reality; the expected unseen tweets are added")
    ap.add_argument("--bid-sell-margin", type=float, default=None,
                    help="ENABLE selling a held bucket when its best bid exceeds our probability by more than this many points "
                         "(take the market's overpayment). Backtest: roughly doubles profit if our tweet count is real-time, HURTS if it lags >=2h")
    ap.add_argument("--no-bid-sell", action="store_true", help="disable the 'sell when market bid > our probability' rule")
    rk = ap.add_argument_group("cost / risk / exit controls (experiments - defaults are NOT backtest-validated)")
    rk.add_argument("--min-net-edge", type=float, default=None, help="required edge in points AFTER fees and slippage allowance")
    rk.add_argument("--slippage-allowance", type=float, default=0.0, help="extra per-share cost assumed in the net edge, in points")
    rk.add_argument("--no-exit-fee", action="store_true", help="do not count a future exit fee in the net edge")
    rk.add_argument("--max-bucket-frac", type=float, default=0.25, help="max cost in one bucket, fraction of equity (0 = off)")
    rk.add_argument("--max-tail-frac", type=float, default=0.40, help="max cost on one side of the most likely bucket, fraction of equity (0 = off)")
    rk.add_argument("--max-event-frac", type=float, default=0.80, help="max total open cost in the event, fraction of equity (0 = off)")
    rk.add_argument("--min-cash-reserve", type=float, default=0.0, help="USDC that must stay in cash after a buy")
    rk.add_argument("--drawdown-stop", type=float, default=0.0, help="no new entries once equity is this fraction below the start (0 = off)")
    rk.add_argument("--max-sell-slippage", type=float, default=3.0, help="never sell deeper than best bid minus this, in points")
    rk.add_argument("--sell-hysteresis", type=float, default=0.0, help="'bid > pred' sells only when bid exceeds pred by this, in points")
    rk.add_argument("--exit-min-ratio", type=float, default=0.0, help="hold a model-driven exit if net proceeds/share < ratio x our probability (0 = off)")
    ap.add_argument("--buy-every", type=int, default=60, help="minutes between buys")
    ap.add_argument("--sell-every", type=int, default=10, help="minutes between ticks / sell checks")
    ap.add_argument("--model-refresh", type=int, default=None, help="minutes between ensemble re-runs")
    ap.add_argument("--pred-source", choices=["light", "calibrated", "ensemble"], default=None,
                    help="calibrated = ensemble total + recalibrated bucket shape (backtested); ensemble = its native probabilities")
    ap.add_argument("--b", type=float, default=1.15, help="multiplier on the ensemble's remaining-tweets forecast")
    ap.add_argument("--start-after-days", type=float, default=None, help="don't buy until this many days after a market opens")
    ap.add_argument("--max-slippage", type=float, default=1.0, help="reject a buy if the average fill is worse than the best ask by this many points")
    ap.add_argument("--model-stale-min", type=int, default=150, help="no NEW entries when the applied forecast is older than this (exits still run)")
    ap.add_argument("--max-count-gap", type=int, default=30, help="no NEW entries when our tweet database is more than this many tweets behind Polymarket")
    ap.add_argument("--backup-dir", default=None, help="durable location (other disk / synced folder) that also receives every checkpoint and the tweet dataset")
    ap.add_argument("--allow-new-state", action="store_true", help="deliberately start a NEW account in a run folder whose old state is gone (otherwise refused)")
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


PRESETS = {      # units as on the command line (percent / percentage points)
    # backtest-selected: src/simulation/backtest/ (train/test split, conservative spread + lagged count)
    "light": dict(pred_source="light", min_pred=10.0, min_mkt=2.0, min_edge=0.0, min_net_edge=2.0, sell_below=0.0, no_bid_sell=True,
                  no_exit_fee=True, start_after_days=4.0, model_refresh=180, top_k=2, max_adds=0, pick_best=True),
    "legacy": dict(pred_source="calibrated", min_pred=8.0, min_mkt=3.0, min_edge=1.0, min_net_edge=0.0, sell_below=4.0, no_bid_sell=False,
                   no_exit_fee=False, start_after_days=2.0, model_refresh=60, top_k=0, max_adds=-1, pick_best=False),
}


def apply_preset(a):
    for k, v in PRESETS[a.strategy].items():
        cur = getattr(a, k, None)
        if cur is None or cur is False:                   # None = not given; False = store_true flag not passed
            setattr(a, k, v)
    if a.pick_random:
        a.pick_best = False
    if a.bid_sell_margin is not None:                     # explicit opt-in beats the preset's 'no bid-sell'
        a.no_bid_sell, a.sell_hysteresis = False, a.bid_sell_margin
    return a


def _main(argv=None):
    a = apply_preset(build_parser().parse_args(argv))
    run_dir = os.path.join(a.runs_dir, a.run_name)
    if a.fresh and os.path.isdir(run_dir):
        for f in os.listdir(run_dir):
            if f.endswith((".json", ".csv", ".png", ".txt", ".log", ".lock")):
                os.remove(os.path.join(run_dir, f))
        shutil.rmtree(os.path.join(run_dir, "checkpoints"), ignore_errors=True)     # --fresh really means fresh
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
                  sell_below=a.sell_below / 100, sell_if_bid_above_pred=not a.no_bid_sell, top_k=a.top_k, max_adds=a.max_adds, pick_best=a.pick_best,
                  min_net_edge=a.min_net_edge / 100, slippage_allowance=a.slippage_allowance / 100, include_exit_fee=not a.no_exit_fee,
                  max_bucket_frac=a.max_bucket_frac, max_tail_frac=a.max_tail_frac, max_event_frac=a.max_event_frac,
                  min_cash_reserve=a.min_cash_reserve, drawdown_stop=a.drawdown_stop, max_sell_slippage=a.max_sell_slippage / 100,
                  sell_hysteresis=a.sell_hysteresis / 100, exit_min_ratio=a.exit_min_ratio)
    try:
        if a.replay:
            feed = ReplayFeed(half_spread=a.half_spread / 100, fee_rate=a.fee_rate, step_min=a.sell_every)
            trader = PaperTrader(feed, rules, run_dir, a.bankroll, a.pred_source, a.buy_every, a.sell_every, a.model_refresh,
                                 a.seed, a.b, False, a.start_after_days, a.max_slippage / 100, chart_every=36)
            st = trader.run_replay(a.replay)
            print(open(os.path.join(run_dir, "summary.txt")).read())
            return 0
        feed = LiveFeed(backup_dir=a.backup_dir)
        trader = PaperTrader(feed, rules, run_dir, a.bankroll, a.pred_source, a.buy_every, a.sell_every, a.model_refresh,
                             a.seed, a.b, not a.no_auto_roll, a.start_after_days, a.max_slippage / 100, a.chart_every, verbose=True,
                             model_stale_min=a.model_stale_min, max_count_gap=a.max_count_gap, max_data_age_h=a.max_data_age_h, count_lag_h=a.count_lag_h,
                             backup_dir=a.backup_dir, allow_new_state=a.allow_new_state)
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
