"""
Post-run analysis of a paper-trading run directory.

    python -m src.simulation.paper_trader.report --run-name live40

Prints a report and writes it to <run dir>/report.txt. Reads only the CSV/JSON files the trader wrote.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]


def _read(path, **kw):
    return pd.read_csv(path, **kw) if os.path.exists(path) else pd.DataFrame()


def build_report(run_dir: str) -> str:
    L = []
    P = lambda *a: L.append(" ".join(str(x) for x in a))
    eq = _read(os.path.join(run_dir, "equity.csv"), parse_dates=["ts"])
    tr = _read(os.path.join(run_dir, "trades.csv"), parse_dates=["ts"])
    dec = _read(os.path.join(run_dir, "decisions.csv"), parse_dates=["ts"])
    dat = _read(os.path.join(run_dir, "data_log.csv"), parse_dates=["ts"])
    fc = _read(os.path.join(run_dir, "forecasts.csv"), parse_dates=["ts"])
    snap = _read(os.path.join(run_dir, "snapshots.csv"), parse_dates=["ts"])
    state = json.load(open(os.path.join(run_dir, "state.json"))) if os.path.exists(os.path.join(run_dir, "state.json")) else {}

    P("=" * 78)
    P(f"PAPER TRADING REPORT - {os.path.basename(run_dir)}")
    P("=" * 78)
    if len(eq):
        span = eq.ts.iloc[-1] - eq.ts.iloc[0]
        P(f"period            : {eq.ts.iloc[0]}  ->  {eq.ts.iloc[-1]}  ({span})")
        P(f"ticks logged      : {len(eq)}")
        gaps = eq.ts.diff().dt.total_seconds().div(60)
        P(f"gaps > 15 min     : {(gaps > 15).sum()}  (largest {gaps.max():.0f} min)  <- time the trader was not running")

    P("\n--- RESULT ---")
    start = state.get("start_cash", np.nan)
    if len(eq):
        last = eq.iloc[-1]
        P(f"start cash        : ${start:.2f}")
        P(f"equity now        : ${last.equity_conservative:.2f}  ({(last.equity_conservative / start - 1) * 100:+.1f}%)   [positions valued at the bid, net of sell fee]")
        P(f"cash / open pos   : ${last.cash:.2f} / {int(last.open_positions)}")
        P(f"realised P&L      : ${last.realized_pnl:+.2f}")
        P(f"fees paid         : ${last.fees_paid:.2f}")
        mx, mn = eq.equity_conservative.max(), eq.equity_conservative.min()
        dd = (eq.equity_conservative.cummax() - eq.equity_conservative).max()
        P(f"equity high / low : ${mx:.2f} / ${mn:.2f}   max drawdown ${dd:.2f}")

    P("\n--- TRADES ---")
    if len(tr):
        P(tr.action.value_counts().to_string())
        buys = tr[tr.action == "BUY"]
        if len(buys):
            P(f"\nbuys: {len(buys)}, total spent ${(buys.notional + buys.fee).sum():.2f}, avg price paid {buys.avg_price.mean() * 100:.1f}%, "
              f"avg our prob at buy {buys.pred.mean() * 100:.1f}% vs ask {buys.ask.mean() * 100:.1f}%")
        sells = tr[tr.action == "SELL"]
        if len(sells):
            P(f"sells: {len(sells)}, realised on sells ${sells.realized_pnl.sum():+.2f}")
            P("sell reasons:", sells.reason.str.replace(r"[\d.]+%", "x%", regex=True).value_counts().to_dict())
        st = tr[tr.action.isin(["SETTLE-WIN", "SETTLE-LOSS"])]
        if len(st):
            P(f"settled positions: {len(st)}  wins {(st.action == 'SETTLE-WIN').sum()}  losses {(st.action == 'SETTLE-LOSS').sum()}  P&L ${st.realized_pnl.sum():+.2f}")
        closed = tr[tr.realized_pnl.notna() & (tr.realized_pnl != "")]
        if len(closed):
            by = closed.groupby("bucket").realized_pnl.sum().sort_values()
            P("\nrealised P&L by bucket:\n" + by.round(2).to_string())
    else:
        P("no trades")

    P("\n--- BUY DECISIONS ---")
    if len(dec):
        P(f"hourly decisions  : {len(dec)}")
        P(f"results           : {dec.result.str.split(':').str[0].str.split(' ').str[0].value_counts().to_dict()}")
        P(f"avg candidates    : {dec.n_candidates.mean():.2f}   hours with >=1 candidate: {(dec.n_candidates > 0).mean() * 100:.0f}%")
        b = dec[dec.chosen.notna() & (dec.chosen != "")]
        if len(b):
            P(f"chosen: avg our prob {b.pred.mean() * 100:.1f}%, avg ask {b.ask.mean() * 100:.1f}%, avg edge {b.edge.mean() * 100:.1f}pt, avg draw prob {b.draw_prob.mean():.2f}")

    P("\n--- DATA QUALITY ---")
    if len(dat):
        P(f"ticks with data   : {len(dat)}   count source: {dat.count_source.value_counts().to_dict()}")
        d = pd.to_numeric(dat["diff"], errors="coerce").dropna()
        if len(d):
            P(f"polymarket - our csv tweet count: mean {d.mean():+.1f}, max {d.abs().max():.0f}  (>5 on {(d.abs() > 5).mean() * 100:.0f}% of ticks; our csv lags XTracker between hourly refreshes)")
        P(f"order books ok    : {(dat.quotes_ok / dat.buckets).mean() * 100:.0f}% average, worst tick {(dat.quotes_ok / dat.buckets).min() * 100:.0f}%")
        P(f"tick duration     : mean {dat.tick_seconds.mean():.1f}s, max {dat.tick_seconds.max():.0f}s")
    log_path = os.path.join(run_dir, "paper_trader.log")
    if os.path.exists(log_path):
        txt = open(log_path, errors="replace").read()
        P(f"log: {len(re.findall(r' ERROR ', txt))} ERROR lines, {len(re.findall(r' WARNING ', txt))} WARNING lines  (see paper_trader.log)")

    P("\n--- FORECASTS ---")
    if len(fc):
        P(f"ensemble runs     : {len(fc)}; predicted final total ranged {fc.total_predicted.min():.0f} .. {fc.total_predicted.max():.0f}, last {fc.total_predicted.iloc[-1]:.0f}")

    P("\n--- OUR PROBABILITY vs MARKET (all ticks, all buckets, from snapshots.csv) ---")
    if len(snap):
        s = snap.dropna(subset=["ask"])
        s = s[(s.ask > 0.02) & (s.ask < 0.9)]
        P(f"average (our prob - ask) over {len(s)} bucket-ticks: {(s.our_prob - s.ask).mean() * 100:+.2f}pt;  correlation {np.corrcoef(s.our_prob, s.ask)[0, 1]:.2f}")
        P("(per-bucket averages)")
        P((s.groupby("bucket").agg(ours=("our_prob", "mean"), ask=("ask", "mean")) * 100).round(1).to_string())
    P("\nfiles: trades.csv decisions.csv equity.csv data_log.csv forecasts.csv snapshots.csv config_history.jsonl paper_trader.log charts_archive/")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-name", required=True)
    ap.add_argument("--runs-dir", default=str(ROOT / "src" / "simulation" / "runs"))
    a = ap.parse_args(argv)
    run_dir = os.path.join(a.runs_dir, a.run_name)
    out = build_report(run_dir)
    print(out)
    with open(os.path.join(run_dir, "report.txt"), "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()
