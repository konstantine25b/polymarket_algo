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

from .procutil import lock_state

ROOT = Path(__file__).resolve().parents[3]


LOG_LINE = re.compile(r"(\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d)(?:,\d+)?([+-]\d\d:\d\d)? (ERROR|WARNING) (.*)")


def parse_log_time(text: str, offset: str = None):
    """Aware UTC timestamp of a log line. An explicit offset wins; a naive stamp (legacy logs) is read as host-local."""
    try:
        if offset:
            return pd.Timestamp(text.replace(" ", "T") + offset).tz_convert("UTC")
        local = datetime.fromisoformat(text.replace(" ", "T")).astimezone()      # naive -> host-local, DST-aware
        return pd.Timestamp(local).tz_convert("UTC")
    except ValueError:
        return None


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
    st_lock, info = lock_state(lock)
    if st_lock == "held":
        running = True
        add("OK", f"process running (pid {info.get('pid', '?')}, holds run.lock)")
    elif st_lock == "free":
        add("CRIT", "run.lock exists but no process holds it - the trader crashed or was stopped; start it again (it resumes)")
        ex = os.path.join(run_dir, "exit_status.json")
        if os.path.exists(ex):
            try:
                e = json.load(open(ex))
                add("INFO", f"   last exit: {e.get('reason')} (code {e.get('exit_code')}) at {e.get('ts_utc')}")
            except Exception:
                pass
    else:
        add("CRIT", "no run.lock - the trader is not running (finished or stopped); start it again to resume")
    hb = os.path.join(run_dir, "heartbeat.json")
    if running and os.path.exists(hb):
        try:
            h = json.load(open(hb))
            hb_age = (now - pd.Timestamp(h["ts_utc"])).total_seconds() / 60
            add("OK" if hb_age <= 15 else "CRIT", f"heartbeat {hb_age:.0f} min ago (ticks {h.get('ticks')}, consecutive tick failures {h.get('fails')})")
        except Exception:
            add("WARN", "heartbeat.json unreadable")

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
        add("OK" if last.count_source in ("polymarket", "xtracker") else "WARN", f"tweet count source: {last.count_source} (count used {last.count_used})")
        d = pd.to_numeric(dat["diff"].tail(6), errors="coerce").dropna()          # diff = polymarket page - XTracker/our data
        if len(d) and (d > 5).all():
            add("WARN", f"Polymarket page is ABOVE XTracker by >5 for the last {len(d)} ticks (diff {d.iloc[-1]:+.0f}): our XTracker data is behind "
                        "(refresh failing, or XTracker's export lags) - no new buys until it catches up; sells use the page count")
        elif len(d) and (d < -5).all():
            add("WARN", f"Polymarket page is BELOW XTracker by >5 for the last {len(d)} ticks (diff {d.iloc[-1]:+.0f}): the page counter looks stuck/lagging. "
                        "Trading uses XTracker; this is not a refresh failure")
        slow = dat.tick_seconds.tail(6).max()
        if slow and slow > 150:       # steps are bounded (books 45s + page scrape 90s): more means a bound is not holding
            add("WARN", f"slow ticks (up to {slow:.0f}s) - network or browser problems")

    # 4) model freshness
    fc = _csv(os.path.join(run_dir, "forecasts.csv"), parse_dates=["ts"])
    if fc.empty:
        add("WARN", "no ensemble forecast recorded yet")
    else:
        age = (now - fc.ts.iloc[-1]).total_seconds() / 60
        add("OK" if age <= model_stale_min else "WARN",
            f"last ensemble forecast {age:.0f} min ago (total {fc.total_predicted.iloc[-1]:.0f}, {fc.days_left.iloc[-1]:.2f} days left then)")

    # 5) errors in the log (new logs carry an explicit UTC offset; legacy naive lines are read as host-local time)
    log_path = os.path.join(run_dir, "paper_trader.log")
    if os.path.exists(log_path):
        recent_err, recent_warn, last_errs, xt_fail = 0, 0, [], 0
        cutoff = now - pd.Timedelta(minutes=60)
        for line in open(log_path, errors="replace"):
            m = LOG_LINE.match(line)
            if not m:
                continue
            t = parse_log_time(m.group(1), m.group(2))
            if t is None:
                continue
            if t >= cutoff:
                if "XTRACKER REFRESH FAILED" in m.group(4) or "tweet data refresh FAILED" in m.group(4):
                    xt_fail += 1
                if m.group(3) == "ERROR":
                    recent_err += 1
                    last_errs.append(m.group(4)[:140])
                else:
                    recent_warn += 1
        add("OK" if recent_err == 0 else ("CRIT" if recent_err >= 5 else "WARN"), f"last 60 min in paper_trader.log: {recent_err} errors, {recent_warn} warnings")
        if xt_fail:
            add("WARN", f"XTracker refresh FAILED {xt_fail}x in the last 60 min - see 'XTRACKER REFRESH FAILED' in paper_trader.log for the exact error (e.g. HTTP 403)")
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
    ap.add_argument("--model-stale-min", type=int, default=150, help="warn when the last ensemble forecast is older than this (new entries are blocked at the same age)")
    a = ap.parse_args(argv)
    level, lines = check(os.path.join(a.runs_dir, a.run_name), a.stale_min, a.model_stale_min)
    print(f"PAPER TRADER STATUS - {a.run_name}  [{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC]")
    for sev, msg in lines:
        print(f"  {sev:4s} {msg}")
    print({0: "=> HEALTHY", 1: "=> WARNINGS - look at the WARN lines", 2: "=> CRITICAL - needs action"}[level])
    return level


if __name__ == "__main__":
    sys.exit(main())
