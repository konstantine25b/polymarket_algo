"""
Fees and order-book fills for the paper trader.

Fee model (Polymarket taker fee, charged in USDC, makers pay nothing):

    fee = shares * rate * (price * (1 - price)) ** exponent        rounded to 5 decimals

`rate` / `exponent` come from each market's own `feeSchedule` (for the Elon tweet markets:
rate 0.05, exponent 1, taker only). Every order here is a market order, i.e. a taker.
"""
from dataclasses import dataclass
from math import floor
from typing import List, Optional, Sequence, Tuple

Level = Tuple[float, float]  # (price, size in shares)


@dataclass(frozen=True)
class FeeSchedule:
    rate: float = 0.05
    exponent: float = 1.0

    @classmethod
    def from_market(cls, market: dict) -> "FeeSchedule":
        """Build from a gamma market dict; no fee if fees are not enabled for the market."""
        if not market.get("feesEnabled"):
            return cls(rate=0.0)
        sched = market.get("feeSchedule") or {}
        return cls(rate=float(sched.get("rate", 0.0)), exponent=float(sched.get("exponent", 1.0)))


def taker_fee(shares: float, price: float, fees: FeeSchedule) -> float:
    return round(shares * fees.rate * (price * (1.0 - price)) ** fees.exponent, 5)


def _floor_shares(x: float, decimals: int) -> float:
    k = 10 ** decimals
    return floor(x * k + 1e-9) / k


@dataclass
class Fill:
    side: str            # "BUY" | "SELL"
    shares: float
    notional: float      # shares * price summed over levels (before fee)
    fee: float
    avg_price: float
    cash_delta: float    # BUY: -(notional + fee)   SELL: +(notional - fee)
    levels_used: int


def buy_with_budget(asks: Sequence[Level], budget: float, fees: FeeSchedule,
                    max_avg_price: Optional[float] = None, share_decimals: int = 2) -> Optional[Fill]:
    """
    Market BUY that spends at most `budget` USDC in total, fee included, walking the ask side
    from the best (lowest) price. Share sizes are floored to `share_decimals`.
    Returns None if nothing can be bought (or the average price would exceed `max_avg_price`).
    """
    remaining = budget
    shares = notional = fee = 0.0
    used = 0
    for price, size in sorted(asks):
        if remaining <= 1e-9 or price <= 0:
            break
        unit_cost = price + fees.rate * (price * (1.0 - price)) ** fees.exponent
        take = _floor_shares(min(size, remaining / unit_cost), share_decimals)
        if take <= 0:
            continue
        level_notional = take * price
        level_fee = taker_fee(take, price, fees)
        shares += take
        notional += level_notional
        fee += level_fee
        remaining -= level_notional + level_fee
        used += 1
    if shares <= 0:
        return None
    avg = notional / shares
    if max_avg_price is not None and avg > max_avg_price + 1e-12:
        return None
    return Fill("BUY", shares, notional, fee, avg, -(notional + fee), used)


def sell_shares(bids: Sequence[Level], shares: float, fees: FeeSchedule,
                share_decimals: int = 2) -> Optional[Fill]:
    """Market SELL of up to `shares`, walking the bid side from the best (highest) price."""
    want = _floor_shares(shares, share_decimals)
    sold = notional = fee = 0.0
    used = 0
    for price, size in sorted(bids, reverse=True):
        if want - sold <= 1e-9:
            break
        take = _floor_shares(min(size, want - sold), share_decimals)
        if take <= 0:
            continue
        sold += take
        notional += take * price
        fee += taker_fee(take, price, fees)
        used += 1
    if sold <= 0:
        return None
    return Fill("SELL", sold, notional, fee, notional / sold, notional - fee, used)
