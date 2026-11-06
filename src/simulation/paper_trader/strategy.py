"""
The trading rules, kept free of I/O so they can be unit-tested and reused by the backtest.

Buy  (every `buy_every_min`, one `stake` per run):
    a bucket is a candidate when
        our probability  >= min_pred                (default 8%)
        market ask       >= min_mkt                 (default 3%)
        our probability  >  market ask + min_edge   (default 1.0 percentage point)
    ONE candidate is drawn at random, with probability proportional to its edge (pred - ask).
Sell (checked every `sell_every_min`, the whole position at the bid):
    our probability < sell_below                    (default 4%)
    OR market bid   > our probability
All probabilities and prices are fractions (0.08 = 8%).
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from .fills import FeeSchedule, fee_per_share, sell_shares


@dataclass
class Rules:
    stake: float = 1.0
    min_pred: float = 0.08
    min_mkt: float = 0.03
    min_edge: float = 0.01
    sell_below: float = 0.04
    sell_if_bid_above_pred: bool = True
    min_sell_usd: float = 0.0       # sells of any size are allowed (set > 0 to skip tiny sells)
    # --- cost-aware entry (B09). Net edge = pred - ask - buy fee - exit fee - slippage allowance must exceed min_net_edge.
    min_net_edge: float = 0.0
    slippage_allowance: float = 0.0
    include_exit_fee: bool = True
    # --- exposure limits as a fraction of current conservative equity (B10). 0 disables a limit.
    max_bucket_frac: float = 0.25   # cost basis in one bucket
    max_tail_frac: float = 0.40     # all buckets on one side of the model's most likely bucket (they all lose together)
    max_event_frac: float = 0.80    # everything open in the event
    min_cash_reserve: float = 0.0   # cash that must remain after a buy
    drawdown_stop: float = 0.0      # stop new entries once equity is this far below the start (0 = off)
    # --- exits (B11)
    max_sell_slippage: float = 0.03 # never sell deeper into the book than best bid - this (absolute price)
    sell_hysteresis: float = 0.0    # 'bid > pred' sells only when bid > pred + this
    exit_min_ratio: float = 0.0     # for 'pred below sell_below' exits: hold if net proceeds/share < ratio * pred (0 = off)
    # --- selection (backtested 'light' preset)
    top_k: int = 0                  # only buckets ranked in the model's top K by probability may be bought (0 = any)
    max_adds: int = -1              # extra buys allowed in a bucket already held (0 = never average down, -1 = unlimited)
    pick_best: bool = False         # buy the candidate with the best net edge instead of a random draw weighted by edge
    # --- sizing: stake is the minimum order ($1). kelly > 0 sizes each buy as kelly * equity * (p - ask) / (1 - ask), at least
    # `stake`, at most `max_stake`. Whatever the rule, an order must be >= `min_shares` shares (Polymarket CLOB min_order_size).
    kelly: float = 0.0
    max_stake: float = 3.0
    min_shares: float = 5.0

    def as_dict(self):
        return asdict(self)


@dataclass
class Quote:
    """Best prices and full depth for one bucket's YES token."""
    bids: List[tuple]   # [(price, size)] any order
    asks: List[tuple]

    @property
    def best_bid(self) -> Optional[float]:
        return max((p for p, _ in self.bids), default=None)

    @property
    def best_ask(self) -> Optional[float]:
        return min((p for p, _ in self.asks), default=None)


def buy_candidates(preds: Dict[str, float], quotes: Dict[str, Quote], rules: Rules, fees: Optional[Dict[str, FeeSchedule]] = None) -> List[dict]:
    """Candidates must pass the raw edge rule AND have a positive edge after fees/slippage (`fees` = fee schedule per bucket)."""
    out = []
    ranked = sorted(preds.values(), reverse=True)
    for bucket, pred in preds.items():
        q = quotes.get(bucket)
        if q is None or q.best_ask is None:
            continue
        if rules.top_k > 0 and sum(1 for v in ranked if v > pred) >= rules.top_k:
            continue                                   # not among the model's top-K buckets
        ask = q.best_ask
        if not (pred >= rules.min_pred and ask >= rules.min_mkt and pred - ask > rules.min_edge + 1e-12):
            continue
        fs = (fees or {}).get(bucket, FeeSchedule(rate=0.0))
        costs = net_costs(ask, fs, rules)
        net = pred - ask - costs
        if net <= rules.min_net_edge + 1e-12:
            continue
        out.append({"bucket": bucket, "pred": pred, "ask": ask, "edge": pred - ask, "est_costs": costs, "net_edge": net})
    return out


def size_stake(rules: Rules, pred: float, ask: float, fees: FeeSchedule, equity: float) -> float:
    """Dollars (fee included) to spend on one buy. Rounded UP to the cent so the 5-share minimum is really met."""
    stake = rules.stake
    if rules.kelly > 0 and ask < 1.0:
        stake = min(max(rules.kelly * equity * max(pred - ask, 0.0) / (1.0 - ask), rules.stake), rules.max_stake)
    stake = max(stake, rules.min_shares * (ask + fee_per_share(ask, fees)))
    return float(np.ceil(stake * 100 - 1e-9) / 100)


def net_costs(price: float, fees: FeeSchedule, rules: Rules) -> float:
    """Per-share cost of getting in (taker fee at `price`) and, conservatively, back out again, plus the slippage allowance."""
    c = fee_per_share(price, fees) + rules.slippage_allowance
    if rules.include_exit_fee:
        c += fee_per_share(price, fees)
    return c


def risk_filter(cands: Sequence[dict], held_cost: Dict[str, float], order: Sequence[str], preds: Dict[str, float], equity: float,
                start_cash: float, cash: float, rules: Rules, buys_in_bucket: Optional[Dict[str, int]] = None) -> Tuple[List[dict], List[Tuple[str, str]]]:
    """
    Keep only candidates that fit the exposure limits. `held_cost` = open cost basis per bucket in this event,
    `order` = bucket titles low -> high. Buckets on the same side of the model's most likely bucket form one tail
    group: they are mutually exclusive outcomes driven by the same forecast error, so they are capped together.
    Returns (eligible, [(bucket, reason)]). A lower ask or a bigger edge never overrides a limit.
    """
    rejected: List[Tuple[str, str]] = []
    modal = max(order, key=lambda t: preds.get(t, 0.0)) if order else None
    idx = {t: i for i, t in enumerate(order)}

    def side(t):
        return 0 if modal is None or idx[t] == idx[modal] else (1 if idx[t] > idx[modal] else -1)
    total = sum(held_cost.values())
    side_cost = {-1: 0.0, 0: 0.0, 1: 0.0}
    for t, c in held_cost.items():
        if t in idx:
            side_cost[side(t)] += c
    eligible = []
    for c in cands:
        t = c["bucket"]
        stake = c.get("stake", rules.stake)
        why = None
        if rules.max_adds >= 0 and buys_in_bucket and buys_in_bucket.get(t, 0) > rules.max_adds:
            why = f"no averaging down: already bought {buys_in_bucket[t]}x (max adds {rules.max_adds})"
        elif rules.drawdown_stop > 0 and equity < start_cash * (1 - rules.drawdown_stop):
            why = f"drawdown stop: equity {equity:.2f} < {(1 - rules.drawdown_stop) * 100:.0f}% of start {start_cash:.2f}"
        elif cash - stake < rules.min_cash_reserve - 1e-9:
            why = f"cash reserve: {cash - stake:.2f} left < {rules.min_cash_reserve:.2f}"
        elif rules.max_bucket_frac > 0 and held_cost.get(t, 0.0) + stake > rules.max_bucket_frac * equity + 1e-9:
            why = f"bucket cap: {held_cost.get(t, 0.0) + stake:.2f} > {rules.max_bucket_frac:.0%} of equity {equity:.2f}"
        elif rules.max_tail_frac > 0 and side(t) != 0 and side_cost[side(t)] + stake > rules.max_tail_frac * equity + 1e-9:
            why = f"tail cap: {side_cost[side(t)] + stake:.2f} > {rules.max_tail_frac:.0%} of equity {equity:.2f}"
        elif rules.max_event_frac > 0 and total + stake > rules.max_event_frac * equity + 1e-9:
            why = f"event cap: {total + stake:.2f} > {rules.max_event_frac:.0%} of equity {equity:.2f}"
        if why:
            rejected.append((t, why))
        else:
            eligible.append(c)
    return eligible, rejected


def choose_buy(cands: Sequence[dict], rng: np.random.Generator, best: bool = False) -> Optional[dict]:
    """Weighted random pick (weight = edge), or with best=True the candidate with the largest net edge.
    Records the draw probability on the returned dict."""
    if not cands:
        return None
    if best:
        chosen = dict(max(cands, key=lambda c: c.get("net_edge", c["edge"])))
        chosen["draw_prob"], chosen["n_candidates"] = 1.0, len(cands)
        return chosen
    w = np.array([c["edge"] for c in cands], float)
    p = w / w.sum()
    i = int(rng.choice(len(cands), p=p))
    chosen = dict(cands[i])
    chosen["draw_prob"] = float(p[i])
    chosen["n_candidates"] = len(cands)
    return chosen


def sell_reason(pred: float, bid: Optional[float], rules: Rules) -> Optional[str]:
    if bid is None:
        return None
    if pred < rules.sell_below:
        return f"pred {pred*100:.1f}% < {rules.sell_below*100:.0f}%"
    if rules.sell_if_bid_above_pred and bid > pred + rules.sell_hysteresis + 1e-12:
        return f"bid {bid*100:.1f}% > pred {pred*100:.1f}%"
    return None


def plan_sell(bids: Sequence[tuple], shares: float, fees: FeeSchedule, pred: float, reason: str, rules: Rules):
    """
    Preview the exit before committing it. Only bid levels within `max_sell_slippage` of the best bid are used
    (so a thin book is sold partially instead of dumped at any price), and a model-driven exit is skipped when the
    net proceeds per share are below `exit_min_ratio` x our own value of the share. Returns (fill|None, why_not).
    """
    best = max((p for p, _ in bids), default=None)
    if best is None:
        return None, "empty bid side"
    floor = best - rules.max_sell_slippage
    usable = [(p, z) for p, z in bids if p >= floor - 1e-12]
    fill = sell_shares(usable, shares, fees)
    if fill is None:
        return None, "no sellable depth within the price limit"
    per_share = fill.cash_delta / fill.shares
    if rules.exit_min_ratio > 0 and reason.startswith("pred") and per_share < rules.exit_min_ratio * pred:
        return None, f"net proceeds {per_share * 100:.2f}c/share below {rules.exit_min_ratio:.0%} of model value {pred * 100:.2f}c"
    return fill, ""


