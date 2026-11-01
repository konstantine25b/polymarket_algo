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
from typing import Dict, List, Optional, Sequence

import numpy as np


@dataclass
class Rules:
    stake: float = 1.0
    min_pred: float = 0.08
    min_mkt: float = 0.03
    min_edge: float = 0.01
    sell_below: float = 0.04
    sell_if_bid_above_pred: bool = True
    min_sell_usd: float = 0.0       # sells of any size are allowed (set > 0 to skip tiny sells)

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


def buy_candidates(preds: Dict[str, float], quotes: Dict[str, Quote], rules: Rules) -> List[dict]:
    out = []
    for bucket, pred in preds.items():
        q = quotes.get(bucket)
        if q is None or q.best_ask is None:
            continue
        ask = q.best_ask
        if pred >= rules.min_pred and ask >= rules.min_mkt and pred - ask > rules.min_edge + 1e-12:
            out.append({"bucket": bucket, "pred": pred, "ask": ask, "edge": pred - ask})
    return out


def choose_buy(cands: Sequence[dict], rng: np.random.Generator) -> Optional[dict]:
    """Weighted random pick; weight = edge. Records the draw probability on the returned dict."""
    if not cands:
        return None
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
    if rules.sell_if_bid_above_pred and bid > pred:
        return f"bid {bid*100:.1f}% > pred {pred*100:.1f}%"
    return None
