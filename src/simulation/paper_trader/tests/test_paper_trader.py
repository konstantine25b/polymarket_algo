import csv
import os

import numpy as np
import pandas as pd
import pytest

from src.simulation.paper_trader.account import PaperAccount
from src.simulation.paper_trader.feeds import Bucket, Event
from src.simulation.paper_trader.fills import FeeSchedule, buy_with_budget, sell_shares, taker_fee
from src.simulation.paper_trader.model import gamma_bucket_probs, map_native_frames, parse_range
from src.simulation.paper_trader.runner import PaperTrader
from src.simulation.paper_trader.strategy import Quote, Rules, buy_candidates, choose_buy, sell_reason

FEES = FeeSchedule(0.05, 1.0)


# ---------------------------------------------------------------- fees and fills
def test_fee_formula_matches_docs_examples():
    assert taker_fee(100, 0.5, FeeSchedule(0.05, 1)) == 1.25          # docs: 100 sh @ $0.50, rate 0.05
    assert taker_fee(100, 0.10, FeeSchedule(0.04, 1)) == 0.36          # docs: finance example
    assert taker_fee(100, 0.05, FEES) == pytest.approx(0.2375)
    assert taker_fee(10, 0.5, FeeSchedule(0.0, 1)) == 0.0


def test_buy_spends_budget_including_fee():
    f = buy_with_budget([(0.05, 1000)], 1.0, FEES)
    assert f.shares == 19.0 or f.shares == 18.99 or 18.9 < f.shares <= 19.1
    assert f.fee == taker_fee(f.shares, 0.05, FEES)
    assert -f.cash_delta <= 1.0 + 1e-9                                # never overspends
    assert -f.cash_delta > 1.0 - 0.06                                 # leaves less than one share's cost unspent


def test_buy_walks_levels_and_respects_depth():
    f = buy_with_budget([(0.05, 5), (0.06, 1000)], 1.0, FEES)
    assert f.levels_used == 2
    assert 0.05 < f.avg_price < 0.06
    assert f.shares > 5


def test_buy_rejected_when_slippage_too_big():
    assert buy_with_budget([(0.05, 5), (0.20, 1000)], 1.0, FEES, max_avg_price=0.06) is None


def test_sell_walks_bids_and_charges_fee():
    f = sell_shares([(0.10, 10), (0.09, 100)], 50, FEES)
    assert f.shares == 50
    assert f.notional == pytest.approx(10 * 0.10 + 40 * 0.09)
    assert f.fee == pytest.approx(taker_fee(10, 0.10, FEES) + taker_fee(40, 0.09, FEES), abs=1e-5)
    assert f.cash_delta == pytest.approx(f.notional - f.fee)


def test_sell_more_than_book_depth_sells_what_exists():
    f = sell_shares([(0.10, 10)], 50, FEES)
    assert f.shares == 10


# ---------------------------------------------------------------- the rules
RULES = Rules()


def q(bid, ask):
    return Quote([(bid, 1000)], [(ask, 1000)])


def test_buy_candidate_boundaries():
    quotes = {"a": q(0.04, 0.05), "b": q(0.025, 0.03), "c": q(0.10, 0.11)}
    # a: pred .0601 vs ask .05 -> edge .0101 passes edge but pred < 8% fails
    assert buy_candidates({"a": 0.0601}, quotes, RULES) == []
    # pred >= 8%, ask >= 3%, edge strictly > 1pt
    assert [c["bucket"] for c in buy_candidates({"a": 0.0801}, quotes, RULES)] == ["a"]
    assert buy_candidates({"a": 0.06}, quotes, RULES) == []                       # edge exactly 1pt is NOT enough
    # b: market ask exactly 3% passes the market minimum; 2.9% would not
    assert [c["bucket"] for c in buy_candidates({"b": 0.10}, quotes, RULES)] == ["b"]
    assert buy_candidates({"b": 0.10}, {"b": q(0.02, 0.029)}, RULES) == []
    # c: pred below ask -> never
    assert buy_candidates({"c": 0.09}, quotes, RULES) == []


def test_weighted_choice_proportional_to_edge():
    cands = [{"bucket": "x", "pred": 0.2, "ask": 0.1, "edge": 0.1}, {"bucket": "y", "pred": 0.13, "ask": 0.1, "edge": 0.03}]
    rng = np.random.default_rng(0)
    picks = [choose_buy(cands, rng)["bucket"] for _ in range(4000)]
    assert abs(picks.count("x") / 4000 - 0.1 / 0.13) < 0.03
    assert choose_buy([], rng) is None


def test_sell_rule():
    assert sell_reason(0.039, 0.02, RULES)                  # pred < 4%
    assert sell_reason(0.10, 0.11, RULES)                   # bid above our probability
    assert sell_reason(0.10, 0.10, RULES) is None          # equal is not "above"
    assert sell_reason(0.10, 0.08, RULES) is None
    assert sell_reason(0.10, 0.12, Rules(sell_if_bid_above_pred=False)) is None


# ---------------------------------------------------------------- model
def test_parse_range_and_probabilities():
    assert parse_range("380-399") == (380, 399) and parse_range("580+")[0] == 580 and parse_range("<20") == (0, 19)
    ranges = [(i, i + 19) for i in range(0, 600, 20)]
    p = gamma_bucket_probs(ranges, so_far=300, rate_per_day=60, days_left=2.0)
    assert p.sum() == pytest.approx(1.0)
    assert (p[:15] < 1e-9).all()                            # below 300 tweets already impossible
    centre = 300 + 1.15 * 60 * 2
    assert abs(np.argmax(p) * 20 + 10 - centre) < 40
    nat = map_native_frames({"380–399": 0.5, "400–419": 0.5}, [(380, 399), (400, 419)])
    assert nat.tolist() == [0.5, 0.5]


# ---------------------------------------------------------------- account accounting
def test_account_conservation_and_persistence(tmp_path):
    a = PaperAccount(str(tmp_path), 30.0)
    t = pd.Timestamp("2026-11-01 12:00", tz="UTC")
    f1 = buy_with_budget([(0.05, 1000)], 1.0, FEES)
    a.buy("e|b", "e", "b", "tok", f1, t)
    f2 = buy_with_budget([(0.06, 1000)], 1.0, FEES)
    a.buy("e|b", "e", "b", "tok", f2, t)
    assert a.cash == pytest.approx(30 - (-f1.cash_delta) - (-f2.cash_delta))
    pos = a.positions["e|b"]
    assert pos["cost_usd"] == pytest.approx(-f1.cash_delta - f2.cash_delta)          # cost basis includes buy fees
    sell = sell_shares([(0.07, 1000)], pos["shares"], FEES)
    a.sell("e|b", sell, t, "test")
    assert "e|b" not in a.positions or a.positions["e|b"]["shares"] < 0.01
    # realised P&L equals the cash change once flat
    assert a.cash - 30 == pytest.approx(a.state["realized_pnl"], abs=1e-6)
    assert a.state["fees_paid"] == pytest.approx(f1.fee + f2.fee + sell.fee)
    again = PaperAccount(str(tmp_path), 999)                                        # reload from disk
    assert again.state == a.state


def test_settlement_pays_one_dollar_per_winning_share(tmp_path):
    a = PaperAccount(str(tmp_path), 30.0)
    t = pd.Timestamp("2026-11-01 12:00", tz="UTC")
    f = buy_with_budget([(0.05, 1000)], 1.0, FEES)
    a.buy("e|w", "e", "w", "tok", f, t)
    cost = a.positions["e|w"]["cost_usd"]
    pnl = a.settle("e|w", True, t)
    assert pnl == pytest.approx(f.shares - cost)
    assert a.cash == pytest.approx(30 - cost + f.shares)
    f2 = buy_with_budget([(0.05, 1000)], 1.0, FEES)
    a.buy("e|l", "e", "l", "tok2", f2, t)
    assert a.settle("e|l", False, t) == pytest.approx(-(-f2.cash_delta))


# ---------------------------------------------------------------- full engine on a fake feed (no network)
class FakeFeed:
    mode = "replay"

    def __init__(self):
        self.books = {"380-399": Quote([(0.10, 500)], [(0.12, 500)]), "400-419": Quote([(0.13, 500)], [(0.15, 500)]),
                      "420-439": Quote([(0.08, 500)], [(0.10, 500)])}

    def quotes(self, event, now):
        return self.books

    def tweet_count(self, event, now):
        return 300

    def forecast(self, event, now, out_dir="", seed=42):
        return {"total_predicted": 420.0, "current_tweets": 300, "time_remaining_days": 2.0, "frames": None}

    def resolution(self, event):
        return {"380-399": False, "400-419": True, "420-439": False}

    def next_event(self, *a):
        return None


def make_event():
    start = pd.Timestamp("2026-10-27 16:00", tz="UTC")
    bks = [Bucket(t, *parse_range(t), "tok-" + t, FEES) for t in ("380-399", "400-419", "420-439")]
    return Event("fake", "Fake market", start, start + pd.Timedelta(days=7), bks)


def test_engine_buys_sells_and_settles(tmp_path):
    feed, ev = FakeFeed(), make_event()
    t = PaperTrader(feed, Rules(), str(tmp_path), 30.0, buy_every_min=60, sell_every_min=10, b=1.0, start_after_days=0, chart_every=1000)
    t.event, t.events["fake"] = ev, ev
    now = ev.start + pd.Timedelta(days=5)                       # 2 days left
    t.tick(now)
    trades = list(csv.DictReader(open(tmp_path / "trades.csv")))
    assert len(trades) <= 1 and (not trades or trades[0]["action"] == "BUY")
    n_buys = t.account.state["n_buys"]
    # an extra tick 10 minutes later must NOT buy again (buy interval is 60 min)
    t.tick(now + pd.Timedelta(minutes=10))
    assert t.account.state["n_buys"] == n_buys
    # an hour later it may buy again
    t.tick(now + pd.Timedelta(minutes=61))
    assert t.account.state["n_buys"] <= n_buys + 1
    # make the market bid exceed our probability -> the position must be sold
    if t.account.positions:
        bucket = next(iter(t.account.positions.values()))["bucket"]
        feed.books[bucket] = Quote([(0.90, 500)], [(0.92, 500)])
        t.tick(now + pd.Timedelta(minutes=70))
        assert bucket not in {p["bucket"] for p in t.account.positions.values()}
    # market ends and resolves -> remaining positions settled, cash never negative
    t.tick(ev.end + pd.Timedelta(minutes=5))
    assert not t.account.positions
    assert t.account.cash >= 0
    for row in csv.DictReader(open(tmp_path / "trades.csv")):
        assert float(row["fee"]) >= 0


def test_never_overspends_bankroll(tmp_path):
    feed, ev = FakeFeed(), make_event()
    t = PaperTrader(feed, Rules(), str(tmp_path), 3.0, buy_every_min=1, sell_every_min=1, b=1.0, start_after_days=0, chart_every=1000)
    t.event, t.events["fake"] = ev, ev
    now = ev.start + pd.Timedelta(days=5)
    for i in range(20):
        t.tick(now + pd.Timedelta(minutes=2 * i))
        assert t.account.cash >= -1e-9
    assert t.account.state["n_buys"] <= 3


# ---------------------------------------------------------------- status check
def test_status_reports_critical_when_not_running(tmp_path):
    from src.simulation.paper_trader.status import check
    level, lines = check(str(tmp_path / "nope"))
    assert level == 2
    d = tmp_path / "run"
    d.mkdir()
    level, lines = check(str(d))                      # exists but nothing running and no ticks
    assert level == 2
    assert any("not running" in m or "no run.lock" in m for _, m in lines)
