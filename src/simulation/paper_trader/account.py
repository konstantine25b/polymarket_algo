"""
Paper account: cash, positions, trade log. Everything is persisted so the trader can be stopped
and restarted without losing state (state.json is replaced atomically after every change).

Accounting rules
- BUY  : cash -= notional + fee; the position's cost basis includes the buy fee.
- SELL : cash += notional - fee; realised P&L = proceeds - (cost basis of the shares sold).
- SETTLE (market resolved): a winning share pays $1, a losing share $0; no fee on redemption.
Conservation check: start_cash + realised_pnl + (cost basis of open positions) + cash_drift == cash,
verified in the tests.
"""
import csv
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional

from .checkpoint import StateMissingError, has_prior_run_evidence, load_latest_valid, restore_into
from .procutil import atomic_write_json, atomic_write_text
from .fills import Fill, FeeSchedule, taker_fee

log = logging.getLogger("paper_trader")

TRADE_FIELDS = ["ts", "action", "event", "bucket", "shares", "avg_price", "notional", "fee", "cash_after",
                "pred", "ask", "bid", "reason", "realized_pnl", "draw_prob", "n_candidates"]
EQUITY_FIELDS = ["ts", "event", "tweets", "cash", "positions_bid_value", "positions_mid_value",
                 "equity_conservative", "equity_mid", "open_positions", "fees_paid", "realized_pnl"]


def _now_iso(ts=None):
    return (ts or datetime.now(timezone.utc)).isoformat(timespec="seconds")


def append_csv(path: str, fields, row: dict):
    """Append one row. If the file already has a different header (an older version of this program wrote it) the
    existing columns are kept and any new columns are added by an atomic rewrite - rows never end up misaligned."""
    fields = list(fields)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerow(row)
        return
    with open(path, newline="") as f:
        existing = next(csv.reader(f), [])
    header = existing
    if not set(fields) <= set(existing):
        header = existing + [c for c in fields if c not in existing]
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
        tmp = path + f".{os.getpid()}.mig"
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore", restval="")
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, path)
    with open(path, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=header, extrasaction="ignore", restval="").writerow(row)


class PaperAccount:
    def __init__(self, run_dir: str, bankroll: float = 30.0, backup_dir: Optional[str] = None, allow_new_state: bool = False):
        self.run_dir = run_dir
        self.backup_dir = backup_dir
        os.makedirs(run_dir, exist_ok=True)
        self.state_path = os.path.join(run_dir, "state.json")
        self.trades_path = os.path.join(run_dir, "trades.csv")
        self.equity_path = os.path.join(run_dir, "equity.csv")
        self.state = None
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path) as f:
                    self.state = json.load(f)
            except ValueError as ex:
                log.error("state.json is corrupt (%s) - trying the checkpoints", ex)
        if self.state is None:
            self.state = self._recover_or_init(bankroll, allow_new_state)

    def _recover_or_init(self, bankroll, allow_new_state):
        dirs = [os.path.join(self.run_dir, "checkpoints")]
        if self.backup_dir:
            dirs.append(os.path.join(self.backup_dir, os.path.basename(os.path.abspath(self.run_dir))))
        payload, bad = load_latest_valid(*dirs)
        if payload is not None:
            restore_into(self.run_dir, payload)
            log.error("STATE RESTORED from checkpoint #%s of %s (cash %.2f) - %d corrupt checkpoint(s) skipped",
                      payload["seq"], payload["ts_utc"], payload["state"]["cash"], len(bad))
            return payload["state"]
        if has_prior_run_evidence(self.run_dir) and not allow_new_state:
            raise StateMissingError(
                f"{self.run_dir} has logs/ledger from an earlier run but no state.json and no valid checkpoint. "
                "Refusing to silently start a fresh account under the same name. Restore the folder, or pass "
                "--allow-new-state to deliberately start over.")
        state = {"start_cash": bankroll, "cash": bankroll, "positions": {}, "realized_pnl": 0.0,
                 "fees_paid": 0.0, "n_buys": 0, "n_sells": 0, "n_settled": 0, "last_buy_ts": None,
                 "created": _now_iso()}
        self.state = state
        self.save()
        return state

    # ---- convenience
    @property
    def cash(self) -> float:
        return self.state["cash"]

    @property
    def positions(self) -> Dict[str, dict]:
        return self.state["positions"]

    def save(self):
        atomic_write_json(self.state_path, self.state)       # unique temp file per writer, fsync, rename

    # ---- trading
    def buy(self, key: str, event: str, bucket: str, token: str, fill: Fill, ts, ctx: Optional[dict] = None):
        ctx = ctx or {}
        s = self.state
        s["cash"] = round(s["cash"] + fill.cash_delta, 8)
        s["fees_paid"] += fill.fee
        s["n_buys"] += 1
        s["last_buy_ts"] = _now_iso(ts)
        pos = s["positions"].setdefault(key, {"event": event, "bucket": bucket, "token": token, "shares": 0.0,
                                              "cost_usd": 0.0, "fees_paid": 0.0, "opened": _now_iso(ts)})
        pos["shares"] = round(pos["shares"] + fill.shares, 8)
        pos["cost_usd"] += fill.notional + fill.fee
        pos["fees_paid"] += fill.fee
        append_csv(self.trades_path, TRADE_FIELDS, {
            "ts": _now_iso(ts), "action": "BUY", "event": event, "bucket": bucket, "shares": fill.shares,
            "avg_price": round(fill.avg_price, 6), "notional": round(fill.notional, 5), "fee": fill.fee,
            "cash_after": round(s["cash"], 5), "realized_pnl": "", **ctx})
        self.save()

    def sell(self, key: str, fill: Fill, ts, reason: str, ctx: Optional[dict] = None):
        ctx = ctx or {}
        s = self.state
        pos = s["positions"][key]
        frac = min(1.0, fill.shares / pos["shares"])
        cost_sold = pos["cost_usd"] * frac
        realized = fill.cash_delta - cost_sold
        s["cash"] = round(s["cash"] + fill.cash_delta, 8)
        s["fees_paid"] += fill.fee
        s["realized_pnl"] += realized
        s["n_sells"] += 1
        pos["shares"] = round(pos["shares"] - fill.shares, 8)
        pos["cost_usd"] -= cost_sold
        if pos["shares"] < 0.005:      # dust (< smallest sellable size) is written off as a loss at settlement
            pos["shares"] = max(pos["shares"], 0.0)
        append_csv(self.trades_path, TRADE_FIELDS, {
            "ts": _now_iso(ts), "action": "SELL", "event": pos["event"], "bucket": pos["bucket"],
            "shares": fill.shares, "avg_price": round(fill.avg_price, 6), "notional": round(fill.notional, 5),
            "fee": fill.fee, "cash_after": round(s["cash"], 5), "reason": reason,
            "realized_pnl": round(realized, 5), **ctx})
        if pos["shares"] <= 0:
            del s["positions"][key]
        self.save()

    def settle(self, key: str, won: bool, ts):
        s = self.state
        pos = s["positions"].pop(key)
        payout = pos["shares"] if won else 0.0
        realized = payout - pos["cost_usd"]
        s["cash"] = round(s["cash"] + payout, 8)
        s["realized_pnl"] += realized
        s["n_settled"] += 1
        append_csv(self.trades_path, TRADE_FIELDS, {
            "ts": _now_iso(ts), "action": "SETTLE-WIN" if won else "SETTLE-LOSS", "event": pos["event"],
            "bucket": pos["bucket"], "shares": pos["shares"], "avg_price": 1.0 if won else 0.0,
            "notional": round(payout, 5), "fee": 0.0, "cash_after": round(s["cash"], 5),
            "reason": "market resolved", "realized_pnl": round(realized, 5)})
        self.save()
        return realized

    # ---- reporting
    def equity(self, quotes_by_key: Dict[str, "object"], fees: Dict[str, FeeSchedule]) -> dict:
        """
        Mark open positions: conservative = sell everything at the best bid net of the taker fee
        (what you'd actually get), mid = at the midpoint (for the chart). Positions without a
        quote are carried at cost.
        """
        bid_val = mid_val = 0.0
        for key, pos in self.positions.items():
            q = quotes_by_key.get(key)
            if q is None or q.best_bid is None:
                bid_val += pos["cost_usd"]
                mid_val += pos["cost_usd"]
                continue
            bid = q.best_bid
            fs = fees.get(key, FeeSchedule())
            bid_val += pos["shares"] * bid - taker_fee(pos["shares"], bid, fs)
            ask = q.best_ask if q.best_ask is not None else bid
            mid_val += pos["shares"] * (bid + ask) / 2.0
        return {"cash": self.cash, "positions_bid_value": bid_val, "positions_mid_value": mid_val,
                "equity_conservative": self.cash + bid_val, "equity_mid": self.cash + mid_val}

    def log_equity(self, ts, event: str, tweets, eq: dict):
        append_csv(self.equity_path, EQUITY_FIELDS, {
            "ts": _now_iso(ts), "event": event, "tweets": tweets,
            "cash": round(eq["cash"], 5), "positions_bid_value": round(eq["positions_bid_value"], 5),
            "positions_mid_value": round(eq["positions_mid_value"], 5),
            "equity_conservative": round(eq["equity_conservative"], 5), "equity_mid": round(eq["equity_mid"], 5),
            "open_positions": len(self.positions), "fees_paid": round(self.state["fees_paid"], 5),
            "realized_pnl": round(self.state["realized_pnl"], 5)})
