"""Charts written to the run directory on every cycle (always the latest; nothing pops up on screen)."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_equity(run_dir: str, start_cash: float):
    eq_path, tr_path = os.path.join(run_dir, "equity.csv"), os.path.join(run_dir, "trades.csv")
    if not os.path.exists(eq_path):
        return
    eq = pd.read_csv(eq_path, parse_dates=["ts"])
    if eq.empty:
        return
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(12, 7.5), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax.plot(eq.ts, eq.equity_conservative, color="#1f77b4", lw=2, label="equity (positions at bid, net of sell fee)")
    ax.plot(eq.ts, eq.equity_mid, color="#7f7f7f", lw=1, ls="--", label="equity (positions at mid)")
    ax.plot(eq.ts, eq.cash, color="#2ca02c", lw=1, alpha=0.7, label="cash")
    ax.axhline(start_cash, color="k", lw=0.8, ls=":", label=f"start \\${start_cash:.0f}")
    if os.path.exists(tr_path):
        tr = pd.read_csv(tr_path, parse_dates=["ts"])
        for action, color, marker in (("BUY", "#2ca02c", "^"), ("SELL", "#d62728", "v"),
                                      ("SETTLE-WIN", "#ff7f0e", "*"), ("SETTLE-LOSS", "#8c564b", "x")):
            t = tr[tr.action == action]
            if len(t):
                y = np.interp(t.ts.astype("int64"), eq.ts.astype("int64"), eq.equity_conservative)
                ax.scatter(t.ts, y, c=color, marker=marker, s=40 if action in ("BUY", "SELL") else 90, label=action, zorder=3)
    last = eq.iloc[-1]
    ax.set_title(f"Paper trading - equity \\${last.equity_conservative:.2f} (start \\${start_cash:.0f}, "
                 f"{(last.equity_conservative/start_cash-1)*100:+.1f}%) | fees paid \\${last.fees_paid:.2f} | "
                 f"realised \\${last.realized_pnl:+.2f}")
    ax.set_ylabel("USD")
    ax.grid(alpha=0.3)
    ax.legend(loc="best", fontsize=8, ncol=2)
    ax2.bar(eq.ts, eq.open_positions, width=0.005, color="#9467bd")
    ax2.set_ylabel("open positions")
    ax2.grid(alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(os.path.join(run_dir, "equity.png"), dpi=110)
    plt.close(fig)


def plot_market(run_dir: str, title: str, buckets, preds, quotes, held, rules, tweets=None):
    """Our probability vs the market's bid/ask for every bucket; held positions highlighted."""
    x = np.arange(len(buckets))
    ours = np.array([preds.get(b, 0.0) for b in buckets]) * 100
    ask = np.array([(quotes[b].best_ask if b in quotes and quotes[b].best_ask is not None else np.nan) for b in buckets]) * 100
    bid = np.array([(quotes[b].best_bid if b in quotes and quotes[b].best_bid is not None else np.nan) for b in buckets]) * 100
    fig, ax = plt.subplots(figsize=(13, 6))
    colors = ["#ff7f0e" if b in held else "#1f77b4" for b in buckets]
    ax.bar(x, ours, color=colors, alpha=0.75, label="our probability (orange = we hold it)")
    ax.plot(x, ask, "v", color="#d62728", label="market ask")
    ax.plot(x, bid, "^", color="#2ca02c", label="market bid")
    ax.axhline(rules.min_pred * 100, color="#9467bd", ls="--", lw=1, label=f"min prediction {rules.min_pred*100:.0f}%")
    ax.axhline(rules.sell_below * 100, color="#8c564b", ls=":", lw=1, label=f"sell below {rules.sell_below*100:.0f}%")
    ax.set_xticks(x)
    ax.set_xticklabels(buckets, rotation=60, fontsize=8)
    ax.set_ylabel("%")
    ax.set_title(title + (f" | tweets so far {tweets}" if tweets is not None else ""))
    ax.grid(alpha=0.3, axis="y")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(run_dir, "market.png"), dpi=110)
    plt.close(fig)


def write_summary(run_dir: str, state: dict, extra: dict):
    lines = [f"start cash        : ${state['start_cash']:.2f}", f"cash now          : ${state['cash']:.2f}",
             f"open positions    : {len(state['positions'])}", f"buys / sells / settled : {state['n_buys']} / {state['n_sells']} / {state['n_settled']}",
             f"fees paid         : ${state['fees_paid']:.4f}", f"realised P&L      : ${state['realized_pnl']:+.4f}"]
    lines += [f"{k:18s}: {v}" for k, v in extra.items()]
    with open(os.path.join(run_dir, "summary.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
