"""
Health check for a running (or finished) paper-trading run. Reads files only; safe to run any time.

    python -m src.simulation.paper_trader.status --run-name live40

Exit code: 0 = healthy, 1 = warnings (look at them), 2 = critical (not running / stale / failing).
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]


def _csv(path, **kw):
    return pd.read_csv(path, **kw) if os.path.exists(path) and os.path.getsize(path) > 0 else pd.DataFrame()


def check(run_dir: str, stale_min: int = 25, model_stale_min: int = 150):
    """Returns (level 0/1/2, list of (severity, message))."""
    out, level = [], 0

    def add(sev, msg):
        nonlocal level
        out.append((sev, msg))
        level = max(level, {"OK": 0, "WARN": 1, "CRIT": 2, "INFO": 0}[sev])

    if not os.path.isdir(run_dir):
        return 2, [("CRIT", f"run folder not found: {run_dir}")]
    now = pd.Timestamp.now(tz="UTC")

    # 1) process
    lock = os.path.join(run_dir, "run.lock")
    running = False
    if os.path.exists(lock):
        try:
            pid = int(open(lock).read().strip())
            os.kill(pid, 0)
            running = True
            add("OK", f"process running (pid {pid})")
        except (ProcessLookupError, ValueError):
            add("CRIT", "run.lock exists but the process is dead - the trader crashed or was killed; start it again (it resumes)")
        except PermissionError:
            running = True
            add("OK", "process running (owned by another user)")
    else:
        add("CRIT", "no run.lock - the trader is not running (finished or stopped); start it again to resume")

    # 2) freshness of the last tick
    eq = _csv(os.path.join(run_dir, "equity.csv"), parse_dates=["ts"])
    if eq.empty:
        add("CRIT", "equity.csv is empty - no tick has completed yet")
    else:
        age = (now - eq.ts.iloc[-1]).total_seconds() / 60
        sev = "OK" if age <= stale_min else ("CRIT" if running else "INFO")
        add(sev, f"last tick {age:.0f} min ago ({eq.ts.iloc[-1]:%Y-%m-%d %H:%M} UTC)" + ("" if age <= stale_min else f"  <- older than {stale_min} min"))

    # 3) data quality of the latest ticks
    dat = _csv(os.path.join(run_dir, "data_log.csv"), parse_dates=["ts"])
    if not dat.empty:
        last = dat.iloc[-1]
        ratio = last.quotes_ok / last.buckets if last.buckets else 0
        add("OK" if ratio >= 0.9 else "WARN", f"order books {int(last.quotes_ok)}/{int(last.buckets)} on the last tick")
        add("OK" if last.count_source == "polymarket" else "WARN", f"tweet count source: {last.count_source} (count used {last.count_used})")
        d = pd.to_numeric(dat["diff"].tail(6), errors="coerce").dropna()
        if len(d) and (d.abs() > 5).all():
            add("WARN", f"our tweet database has differed from Polymarket by >5 for the last {len(d)} ticks (diff {d.iloc[-1]:+.0f}) - XTracker refresh may be failing")
        slow = dat.tick_seconds.tail(6).max()
        if slow and slow > 240:
            add("WARN", f"slow ticks (up to {slow:.0f}s) - network or browser problems")

    # 4) model freshness
    fc = _csv(os.path.join(run_dir, "forecasts.csv"), parse_dates=["ts"])
    if fc.empty:
        add("WARN", "no ensemble forecast recorded yet")
    else:
        age = (now - fc.ts.iloc[-1]).total_seconds() / 60
        add("OK" if age <= model_stale_min else "WARN",
            f"last ensemble forecast {age:.0f} min ago (total {fc.total_predicted.iloc[-1]:.0f}, {fc.days_left.iloc[-1]:.2f} days left then)")

    # 5) errors in the log (local-time stamps)
    log_path = os.path.join(run_dir, "paper_trader.log")
    if os.path.exists(log_path):
        recent_err, recent_warn, last_errs = 0, 0, []
        cutoff = datetime.now() - pd.Timedelta(minutes=60).to_pytimedelta()
        for line in open(log_path, errors="replace"):
            m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ (ERROR|WARNING) (.*)", line)
            if not m:
                continue
            try:
                t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if t >= cutoff:
                if m.group(2) == "ERROR":
                    recent_err += 1
                    last_errs.append(m.group(3)[:140])
                else:
                    recent_warn += 1
        add("OK" if recent_err == 0 else ("CRIT" if recent_err >= 5 else "WARN"), f"last 60 min in paper_trader.log: {recent_err} errors, {recent_warn} warnings")
        for e in last_errs[-3:]:
            add("INFO", f"   error: {e}")

    # 6) account
    sp = os.path.join(run_dir, "state.json")
    if os.path.exists(sp):
        st = json.load(open(sp))
        eqv = eq.equity_conservative.iloc[-1] if not eq.empty else float("nan")
        add("INFO", f"account: cash ${st['cash']:.2f} | equity ${eqv:.2f} (start ${st['start_cash']:.2f}) | open positions {len(st['positions'])} | "
                    f"buys {st['n_buys']} sells {st['n_sells']} settled {st['n_settled']} | fees ${st['fees_paid']:.4f} | realised {st['realized_pnl']:+.2f}")
        if st["cash"] < -1e-6:
            add("CRIT", "NEGATIVE CASH - accounting bug, stop and investigate")
    dec = _csv(os.path.join(run_dir, "decisions.csv"), parse_dates=["ts"])
    if not dec.empty:
        last = dec.iloc[-1]
        add("INFO", f"last buy decision {last.ts:%Y-%m-%d %H:%M} UTC: {last.result} ({int(last.n_candidates)} candidates); {len(dec)} decisions so far")
    return level, out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-name", required=True)
    ap.add_argument("--runs-dir", default=str(ROOT / "src" / "simulation" / "runs"))
    ap.add_argument("--stale-min", type=int, default=25, help="critical if the last tick is older than this")
    a = ap.parse_args(argv)
    level, lines = check(os.path.join(a.runs_dir, a.run_name), a.stale_min)
    print(f"PAPER TRADER STATUS - {a.run_name}  [{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC]")
    for sev, msg in lines:
        print(f"  {sev:4s} {msg}")
    print({0: "=> HEALTHY", 1: "=> WARNINGS - look at the WARN lines", 2: "=> CRITICAL - needs action"}[level])
    return level


if __name__ == "__main__":
    sys.exit(main())
