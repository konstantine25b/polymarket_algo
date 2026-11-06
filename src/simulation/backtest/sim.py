"""
Fast hourly simulator of the trading rules on the backtest table (one fresh bankroll per weekly market).

Execution model (deliberately conservative, there is no historical order-book depth):
  ask = mid + half_spread, bid = mid - half_spread, taker fee = shares * fee_rate * p * (1 - p) on every buy and sell,
  a fixed dollar stake per buy (fee included), unlimited depth at the touch.
Rules (all knobs in `Strat`):
  blend   w * light_model + (1 - w) * normalised market mid  = the probability we trade on
  top_k   only buckets ranked in the top K by that probability may be bought (the user's "top 4-5" idea)
  min_p, min_edge (after buy fee and, if sells are enabled, an exit fee), min_ask
  max_adds   extra buys allowed in a bucket already held (0 = never average down)
  exposure caps as a fraction of the starting bankroll
  sell_below (None = hold to settlement)
"""
from dataclasses import dataclass, replace
from typing import List, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Strat:
    w: float = 0.5
    top_k: int = 5
    min_p: float = 0.08
    min_edge: float = 0.02
    min_ask: float = 0.02
    max_adds: int = 0
    stake: float = 1.0
    buy_every_h: int = 1
    start_after_h: float = 0.0
    stop_before_h: float = 0.0
    sell_below: Optional[float] = None
    max_bucket_frac: float = 0.25
    max_event_frac: float = 0.8
    fee_rate: float = 0.05
    half_spread: float = 0.01
    bankroll: float = 40.0


def prep(df: pd.DataFrame):
    """Group the table into per-market numpy blocks."""
    evs = []
    for slug, g in df.groupby("slug", sort=False):
        g = g.sort_values("t")
        mid = np.vstack(g.mid.values)
        model = np.vstack(g.model.values)
        mk = np.nan_to_num(mid, nan=0.0)
        s = mk.sum(axis=1, keepdims=True)
        mk = np.where(s > 0, mk / np.where(s > 0, s, 1), 1.0 / mid.shape[1])
        evs.append({"slug": slug, "end": g.t.iloc[-1], "mid": mid, "model": model, "mk": mk, "into": g.hours_into.values,
                    "left": g.hours_left.values, "winner": int(g.winner.iloc[0])})
    evs.sort(key=lambda e: e["end"])
    return evs


def run_event(e, S: Strat):
    cash, nb = S.bankroll, e["mid"].shape[1]
    shares, cost, adds = np.zeros(nb), np.zeros(nb), np.zeros(nb, int)
    fees_paid, buys, sells = 0.0, 0, 0
    for i in range(len(e["into"])):
        mid = e["mid"][i]
        ok = np.isfinite(mid)
        ask = np.where(ok, np.minimum(mid + S.half_spread, 0.99), np.nan)
        bid = np.where(ok, np.maximum(mid - S.half_spread, 0.001), np.nan)
        p = S.w * e["model"][i] + (1 - S.w) * e["mk"][i]
        if S.sell_below is not None:
            for b in np.nonzero((shares > 0) & ok & (p < S.sell_below))[0]:
                fee = shares[b] * S.fee_rate * bid[b] * (1 - bid[b])
                cash += shares[b] * bid[b] - fee
                fees_paid += fee
                shares[b], cost[b], adds[b] = 0.0, 0.0, 0
                sells += 1
        if i % S.buy_every_h or e["into"][i] < S.start_after_h or e["left"][i] <= S.stop_before_h:
            continue
        if cash < S.stake:
            continue
        rank = (-p).argsort().argsort()                                   # 0 = most likely bucket
        fee_ps = S.fee_rate * ask * (1 - ask)
        exit_fee = fee_ps if S.sell_below is not None else 0.0
        net = p - ask - fee_ps - exit_fee
        cand = ok & (rank < S.top_k) & (p >= S.min_p) & (net > S.min_edge) & (ask >= S.min_ask)
        cand &= (shares == 0) | (adds < S.max_adds)
        cand &= (cost + S.stake <= S.max_bucket_frac * S.bankroll + 1e-9) & (cost.sum() + S.stake <= S.max_event_frac * S.bankroll + 1e-9)
        if not cand.any():
            continue
        b = int(np.argmax(np.where(cand, net, -9)))
        sh = S.stake / (ask[b] + fee_ps[b])
        f = sh * fee_ps[b]
        cash -= S.stake
        fees_paid += f
        if shares[b] > 0:
            adds[b] += 1
        shares[b] += sh
        cost[b] += S.stake
        buys += 1
    cash += shares[e["winner"]]                                             # settlement: winner pays $1
    return {"pnl": cash - S.bankroll, "buys": buys, "sells": sells, "fees": fees_paid, "spent": float(cost.sum()) + 0.0}


def evaluate(evs: List[dict], S: Strat):
    rows = [run_event(e, S) for e in evs]
    pnl = np.array([r["pnl"] for r in rows])
    buys = sum(r["buys"] for r in rows)
    return {"n": len(evs), "total": pnl.sum(), "mean": pnl.mean(), "median": float(np.median(pnl)), "std": pnl.std(),
            "worst": pnl.min(), "best": pnl.max(), "win_rate": float((pnl > 0).mean()), "buys": buys,
            "bad_weeks": float((pnl < -0.5 * S.bankroll).mean()), "fees": sum(r["fees"] for r in rows)}
