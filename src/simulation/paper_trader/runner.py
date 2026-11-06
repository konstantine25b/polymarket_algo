"""
The paper-trading engine.

One tick (every `sell_every_min`, default 10 minutes):
    1. settle any finished market that has resolved
    2. roll to the next weekly market when the current one has ended
    3. read the order books + tweet count, turn the latest forecast into bucket probabilities
    4. SELL checks for every open position (whole position, at the bid, taker fee charged)
    5. BUY (only once per `buy_every_min`, default 60): draw ONE bucket at random among the
       candidates (weight = edge) and market-buy `stake` USDC (fee included) from the real book
    6. log equity, rewrite charts, save state

Everything is persisted in the run directory; the loop survives network/model errors and can be
stopped (Ctrl-C) and restarted without losing anything.
"""
import csv
import json
import logging
import os
import random
import shutil
import signal
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Dict, Optional

import numpy as np
import pandas as pd

from .account import PaperAccount, append_csv
from .console import Console, WIDTH
from .charts import plot_equity, plot_market, write_summary
from .feeds import Event, LiveFeed, ReplayFeed
from .fills import FeeSchedule, buy_with_budget, sell_shares, taker_fee
from .procutil import atomic_write_json, write_heartbeat
from .model import CalibratedModel, ForecastError, NativeEnsembleModel, validate_forecast
from .strategy import Quote, Rules, buy_candidates, choose_buy, sell_reason

log = logging.getLogger("paper_trader")
DATA_FIELDS = ["ts", "event", "polymarket_count", "csv_count", "diff", "csv_newest_tweet", "count_used", "count_source",
               "quotes_ok", "buckets", "model_age_min", "tick_seconds", "note", "fc_state", "fc_fails", "fc_last_failure"]
SNAPSHOT_FIELDS = ["ts", "event", "bucket", "our_prob", "bid", "ask", "bid_size_best", "ask_size_best", "bid_depth_top5",
                   "ask_depth_top5", "held_shares", "tweets", "days_left"]
DECISION_FIELDS = ["ts", "event", "tweets", "days_left", "cash", "n_candidates", "chosen", "pred", "ask", "edge",
                   "draw_prob", "result", "candidates"]


class PaperTrader:
    def __init__(self, feed, rules: Rules, run_dir: str, bankroll: float = 30.0, pred_source: str = "calibrated",
                 buy_every_min: int = 60, sell_every_min: int = 10, model_refresh_min: int = 60, seed: int = 42,
                 b: float = 1.15, auto_roll: bool = True, start_after_days: float = 2.0, max_slippage: float = 0.01,
                 chart_every: int = 1, verbose: bool = False, model_stale_min: int = 150, max_count_gap: int = 30):
        self.con = Console(run_dir, verbose)
        self.feed, self.rules, self.run_dir = feed, rules, run_dir
        self.pred_source, self.buy_every, self.sell_every = pred_source, buy_every_min, sell_every_min
        self.model_refresh, self.auto_roll = model_refresh_min, auto_roll
        self.start_after_days, self.max_slippage, self.chart_every = start_after_days, max_slippage, chart_every
        self.account = PaperAccount(run_dir, bankroll)
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.model = CalibratedModel(b) if pred_source == "calibrated" else NativeEnsembleModel()
        self.event: Optional[Event] = None
        self.events: Dict[str, Event] = {}          # every event we hold (or held) positions in
        self.tweets: Optional[int] = None
        self.ticks = 0
        self._forecast_thread: Optional[threading.Thread] = None
        self._forecast_result = None
        self.model_stale_min, self.max_count_gap = model_stale_min, max_count_gap
        self._jitter = random.Random(seed + 1)          # separate stream: backoff jitter must not perturb the buy draws
        self._reset_forecast_state()
        self._stop = False
        self._warned_min_order = set()
        self._mono, self._sleep, self._wall = time.monotonic, time.sleep, time.time      # injectable clocks (tests)
        self._last_beat = 0.0
        self._fails = 0

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _key(slug, bucket):
        return f"{slug}|{bucket}"

    def _bucket(self, event, title):
        return next((b for b in event.buckets if b.title == title), None)

    # ------------------------------------------------------------------ forecast lifecycle (B06/B07/B08)
    # States: idle -> in_flight -> (accepted | failed). All state is mutated on the tick thread only; the worker thread
    # just hands back a result or a failure reason. last_attempt / last_success / last_failure are kept separately.
    FORECAST_SCHEMA = 1

    def _reset_forecast_state(self):
        self.model = CalibratedModel(self.model.b) if self.pred_source == "calibrated" else NativeEnsembleModel()
        self._last_forecast_at = None            # generation time of the forecast currently applied (accepted-model age)
        self._last_attempt_at = None
        self._last_failure = None
        self._fail_count = 0
        self._next_retry_at = None
        self._forecast_result = None
        self._restore_tried = None

    @property
    def forecast_state(self) -> str:
        return "in_flight" if (self._forecast_thread is not None and self._forecast_thread.is_alive()) else "idle"

    def model_age_min(self, now) -> Optional[float]:
        return None if self._last_forecast_at is None else (now - self._last_forecast_at) / pd.Timedelta(minutes=1)

    def _forecast_path(self):
        return os.path.join(self.run_dir, "forecast_state.json")

    def _persist_forecast(self, fc: dict, event: Event, generated_at: pd.Timestamp, now: pd.Timestamp):
        atomic_write_json(self._forecast_path(), {
            "schema": self.FORECAST_SCHEMA, "event_slug": event.slug, "pred_source": self.pred_source,
            "generated_at": generated_at.isoformat(), "applied_at": now.isoformat(),
            "forecast": {k: fc.get(k) for k in ("total_predicted", "current_tweets", "time_remaining_days", "frames",
                                                  "event_slug", "data_sha256", "data_newest", "generated_for")},
            "model": self.model.to_dict()})

    def _restore_forecast(self, event: Event, now: pd.Timestamp) -> bool:
        """Re-load the last applied forecast after a restart, but only if it is valid, for this event, this prediction
        source and younger than the stale limit. Anything else is ignored (the model stays unready: fail closed)."""
        self._restore_tried = event.slug
        path = self._forecast_path()
        if not os.path.exists(path):
            return False
        try:
            with open(path) as f:
                st = json.load(f)
            if st.get("schema") != self.FORECAST_SCHEMA:
                raise ForecastError(f"schema {st.get('schema')!r}")
            if st.get("event_slug") != event.slug or st.get("pred_source") != self.pred_source:
                raise ForecastError(f"saved forecast is for {st.get('event_slug')}/{st.get('pred_source')}")
            gen = pd.Timestamp(st["generated_at"])
            gen = gen.tz_localize("UTC") if gen.tzinfo is None else gen.tz_convert("UTC")
            if gen - now > pd.Timedelta(minutes=5):
                raise ForecastError("saved forecast is from the future")
            age = (now - gen) / pd.Timedelta(minutes=1)
            if age > self.model_stale_min:
                raise ForecastError(f"saved forecast is {age:.0f} min old (limit {self.model_stale_min})")
            fc = st["forecast"]
            validate_forecast(fc, event.slug, native=self.pred_source != "calibrated")
            fresh = CalibratedModel(self.model.b) if self.pred_source == "calibrated" else NativeEnsembleModel()
            if self.pred_source == "calibrated":
                fresh.update(fc["total_predicted"], fc["current_tweets"], fc["time_remaining_days"], gen)
            else:
                fresh.update_frames(fc["frames"], gen)
        except Exception as ex:
            log.warning("saved forecast not restored (%s) - waiting for a fresh one", ex)
            return False
        self.model, self._last_forecast_at = fresh, gen
        log.info("restored saved forecast for %s generated %s (%.0f min old)", event.slug, gen.isoformat(timespec="seconds"), age)
        return True

    def _apply_forecast(self, fc: dict, event: Event, now: pd.Timestamp, generated_at: Optional[pd.Timestamp] = None):
        """Validate and apply a finished forecast. Raises ForecastError (model left exactly as it was) if it is unusable."""
        generated_at = generated_at if generated_at is not None else now
        if not isinstance(fc, dict):
            raise ForecastError(f"no usable forecast ({type(fc).__name__})")
        fc = dict(fc)
        fc.setdefault("event_slug", event.slug)
        validate_forecast(fc, event.slug, now=now, native=self.pred_source != "calibrated")
        candidate = CalibratedModel(self.model.b) if self.pred_source == "calibrated" else NativeEnsembleModel()
        if self.pred_source == "calibrated":
            candidate.update(fc["total_predicted"], fc["current_tweets"], fc["time_remaining_days"], now)
        else:
            candidate.update_frames(fc["frames"], now)
        self.model = candidate                                     # swap only after everything validated
        self._last_forecast_at = generated_at
        self._fail_count, self._last_failure, self._next_retry_at = 0, None, None
        self._persist_forecast(fc, event, generated_at, now)
        append_csv(os.path.join(self.run_dir, "forecasts.csv"), ["ts", "event", "total_predicted", "current_tweets", "days_left", "models"],
                   {"ts": now.isoformat(), "event": event.slug, "total_predicted": round(fc["total_predicted"], 2),
                    "current_tweets": fc["current_tweets"], "days_left": round(fc["time_remaining_days"], 3),
                    "models": json.dumps(fc.get("model_contributions", {}))})
        log.info("forecast updated: total %.1f (tweets so far %s, %.2f days left)", fc["total_predicted"],
                 fc["current_tweets"], fc["time_remaining_days"])
        if fc.get("report"):
            self.con.banner("MODEL FORECAST - the ensemble was re-run", "#")
            self.con.say(fc["report"])
            if self.pred_source == "calibrated":
                self.con.say("")
                self.con.say(f"  calibrated model: remaining-tweet rate = {self.model.rate:.1f} tweets/day (from the ensemble total), "
                             f"x{self.model.b} bias correction, Gamma spread; recomputed every tick from the live tweet count")
            if fc.get("verbose_log"):
                self.con.say(f"  (the ensemble's full training output is saved in {fc['verbose_log']})")

    def _forecast_failed(self, reason: str, now: pd.Timestamp):
        """Record a failure and schedule the next attempt with exponential backoff + jitter (5, 10, 20, ... max 60 min)."""
        self._fail_count += 1
        self._last_failure = reason
        delay = min(60.0, 5.0 * 2 ** (self._fail_count - 1)) * (0.8 + 0.4 * self._jitter.random())
        self._next_retry_at = now + pd.Timedelta(minutes=delay)
        log.error("forecast attempt failed (%d in a row): %s - next try in %.0f min; new entries are blocked once the "
                  "applied forecast is older than %d min", self._fail_count, reason, delay, self.model_stale_min)

    def _refresh_model(self, event: Event, now: pd.Timestamp, blocking=False):
        """Run the (slow) forecast in the background; pick the result up on a later tick. At most one job in flight."""
        if self._restore_tried != event.slug and not self.model.ready:
            self._restore_forecast(event, now)
        if self._forecast_result is not None:
            res, self._forecast_result = self._forecast_result, None
            kind, payload, launched, slug = res
            if slug != event.slug:
                log.warning("discarding a forecast computed for %s (now trading %s)", slug, event.slug)
            elif kind == "ok":
                try:
                    self._apply_forecast(payload, event, now, launched)
                except ForecastError as ex:
                    self._forecast_failed(f"forecast rejected: {ex}", now)
            else:
                self._forecast_failed(payload, now)
        if self.forecast_state == "in_flight":
            return
        refresh_due = self._last_forecast_at is None or (now - self._last_forecast_at) >= pd.Timedelta(minutes=self.model_refresh)
        retry_ok = self._next_retry_at is None or now >= self._next_retry_at
        if not (refresh_due and retry_ok):
            return
        self._last_attempt_at = now
        if blocking or self.feed.mode == "replay":
            fc = self.feed.forecast(event, now, self.run_dir, self.seed)
            try:
                self._apply_forecast(fc, event, now, now)
            except ForecastError as ex:
                self._forecast_failed(f"{ex}", now)
        else:
            launched, slug = now, event.slug

            def work():
                try:
                    fc = self.feed.forecast(event, launched, self.run_dir, self.seed)
                    self._forecast_result = ("ok", fc, launched, slug) if fc is not None else ("fail", "worker/refresh returned no forecast", launched, slug)
                except Exception as ex:
                    self._forecast_result = ("fail", f"worker raised {ex!r}", launched, slug)
            self._forecast_thread = threading.Thread(target=work, daemon=True)
            self._forecast_thread.start()

    def buy_block_reason(self, now: pd.Timestamp, poly, local) -> Optional[str]:
        """Why NEW entries must not happen right now (None = allowed). Exits are never blocked by this."""
        if not self.model.ready or self._last_forecast_at is None:
            return "no valid forecast"
        age = self.model_age_min(now)
        if age > self.model_stale_min:
            return f"forecast is stale ({age:.0f} min old, limit {self.model_stale_min})"
        if poly is not None and local is not None and poly - local > self.max_count_gap:
            return f"tweet data is stale (our database is {poly - local} tweets behind Polymarket, limit {self.max_count_gap})"
        return None

    # ------------------------------------------------------------------ settlement / rolling
    def _settle_finished(self, now: pd.Timestamp):
        slugs = {p["event"] for p in self.account.positions.values()}
        for slug in slugs:
            ev = self.events.get(slug)
            if ev is None:
                try:
                    ev = self.events[slug] = self.feed.load_event(slug)
                except Exception as ex:
                    log.warning("cannot load %s to settle: %s", slug, ex)
                    continue
            if now < ev.end:
                continue
            try:
                res = self.feed.resolution(ev)
            except Exception as ex:
                log.warning("resolution check failed for %s: %s", slug, ex)
                continue
            if res is None:
                log.info("%s ended, waiting for resolution (%d open positions)", slug,
                         sum(1 for p in self.account.positions.values() if p["event"] == slug))
                continue
            winner = next((t for t, w in res.items() if w), None)
            for key, pos in list(self.account.positions.items()):
                if pos["event"] == slug:
                    pnl = self.account.settle(key, bool(res.get(pos["bucket"], False)), now)
                    log.info("SETTLED %s %s -> %s  P&L %+.2f", slug, pos["bucket"],
                             "WIN" if res.get(pos["bucket"]) else "loss", pnl)
                    self.con.say(f"  SETTLED  {pos['bucket']:>9s}  {'WIN  (pays $1/share)' if res.get(pos['bucket']) else 'loss (worth $0)':22s}  P&L {pnl:+.2f}")
            log.info("%s resolved: winning bucket %s | cash now $%.2f", slug, winner, self.account.cash)
            self.con.banner(f"MARKET RESOLVED: {slug}  -> winning bucket {winner}  | cash now ${self.account.cash:.2f}")

    def _roll_if_needed(self, now: pd.Timestamp) -> bool:
        """Returns True if there is a live market to trade right now (rolling to the next one if needed)."""
        if self.event is not None and now < self.event.end:
            return True
        if self.event is not None:
            self.events[self.event.slug] = self.event
            if not self.auto_roll:
                return False
        after = self.event.end if self.event is not None else now
        nxt = self.feed.next_event(after, now) if self.feed.mode == "live" else None
        if nxt is None:
            log.info("no live weekly market to trade yet - waiting")
            return False
        self.event = self.feed.load_event(nxt)
        self.events[nxt] = self.event
        self.account.state["current_slug"] = nxt
        self.account.save()
        self._reset_forecast_state()
        log.info("now trading %s (%s -> %s)", nxt, self.event.start, self.event.end)
        self.con.banner(f"NOW TRADING: {self.event.title}   ({self.event.start} -> {self.event.end})")
        return True

    # ------------------------------------------------------------------ one tick
    def tick(self, now: pd.Timestamp):
        acct, rules = self.account, self.rules
        self._settle_finished(now)
        if not self._roll_if_needed(now):
            self._log_equity_only(now)
            return
        ev = self.event
        t_start = time.time()
        days_left = ev.days_left(now)
        self.con.banner(f"TICK #{self.ticks + 1}  |  {now.tz_convert('US/Eastern'):%a %b %d %Y %H:%M:%S} ET  |  {ev.title}  |  {days_left:.2f} days left")
        quotes = self.feed.quotes(ev, now)
        # ---- tweet count: Polymarket's own number (what the market resolves on) with our CSV as cross-check/fallback
        poly = self.feed.tweet_count(ev, now)
        try:
            local, newest = self.feed.local_count(ev, now)
        except Exception as ex:
            log.warning("local tweet count failed: %s", ex)
            local, newest = None, None
        note = ""
        if poly is not None:
            self.tweets, source = poly, "polymarket"
            if local is not None and abs(poly - local) > 5:
                note = f"count mismatch: polymarket {poly} vs our data {local} (our data may lag XTracker)"
                log.warning(note)
        elif local is not None:
            self.tweets, source = local, "local_csv"
            note = "polymarket count unavailable - using our own tweet data"
            log.warning(note)
        else:
            source = "last_known"
            note = "no tweet count available - using the last known value"
            log.warning(note)
        log.info("data: polymarket count %s | our csv count %s (newest tweet %s) | %d/%d order books",
                 poly, local, newest, len(quotes), len(ev.buckets))
        self._show_tweet_check(poly, local, newest, len(quotes), len(ev.buckets))
        age = None if self._last_forecast_at is None else round(self.model_age_min(now), 1)
        append_csv(os.path.join(self.run_dir, "data_log.csv"), DATA_FIELDS, {
            "ts": now.isoformat(timespec="seconds"), "event": ev.slug, "polymarket_count": poly, "csv_count": local,
            "diff": (poly - local) if (poly is not None and local is not None) else "", "csv_newest_tweet": newest,
            "count_used": self.tweets, "count_source": source, "quotes_ok": len(quotes), "buckets": len(ev.buckets),
            "model_age_min": age, "tick_seconds": round(time.time() - t_start, 1), "note": note,
            "fc_state": self.forecast_state, "fc_fails": self._fail_count, "fc_last_failure": (self._last_failure or "")[:120]})
        self._refresh_model(ev, now, blocking=self.ticks == 0 and not self.model.ready)
        if not self.model.ready or self.tweets is None or not quotes:
            log.info("waiting for data (model ready=%s, tweets=%s, quotes=%d)", self.model.ready, self.tweets, len(quotes))
            self.con.say("  waiting for the first ensemble forecast / data before any decision is possible")
            self._log_equity_only(now, quotes)
            return
        titles = [b.title for b in ev.buckets]
        try:
            probs = self.model.probs(ev.ranges, so_far=self.tweets, days_left=days_left)
        except ForecastError as ex:
            log.error("cannot compute bucket probabilities (%s) - no decisions this tick", ex)
            self.con.say(f"  probabilities unavailable ({ex}) - no decisions this tick")
            self._log_equity_only(now, quotes)
            return
        preds = dict(zip(titles, probs.tolist()))
        self._write_snapshot(ev, now, titles, preds, quotes, days_left)
        self._show_market(ev, titles, preds, quotes, days_left)

        # ---- SELL checks
        for key, pos in list(acct.positions.items()):
            if pos["event"] != ev.slug:
                continue
            q, b = quotes.get(pos["bucket"]), self._bucket(ev, pos["bucket"])
            if q is None or b is None or q.best_bid is None:
                continue
            reason = sell_reason(preds.get(pos["bucket"], 0.0), q.best_bid, rules)
            if not reason:
                continue
            fill = sell_shares(q.bids, pos["shares"], b.fees)
            if fill is None or fill.notional < rules.min_sell_usd:
                if key not in self._warned_min_order:
                    log.info("SELL signal for %s (%s) but nothing could be sold (position under 0.01 shares or empty bid side) - holding",
                             pos["bucket"], reason)
                    self._warned_min_order.add(key)
                continue
            acct.sell(key, fill, now, reason, {"pred": round(preds.get(pos["bucket"], 0.0), 5), "bid": q.best_bid, "ask": q.best_ask})
            log.info("SELL %s: %.2f sh @ %.3f, fee %.4f (%s)  realised so far %+.2f", pos["bucket"], fill.shares,
                     fill.avg_price, fill.fee, reason, acct.state["realized_pnl"])
            self.con.section("SELL EXECUTED")
            self.con.say(f"  bucket {pos['bucket']}: sold {fill.shares:.2f} shares at an average {fill.avg_price * 100:.2f}%  (best bid {q.best_bid * 100:.2f}%)")
            self.con.say(f"  reason        : {reason}")
            self.con.say(f"  proceeds      : ${fill.notional:.4f} - taker fee ${fill.fee:.4f} = ${fill.cash_delta:.4f}   | cash now ${acct.cash:.2f}")
            self.con.say(f"  realised P&L on this position: {acct.state['realized_pnl']:+.4f} cumulative")

        # ---- BUY (once per buy interval)
        since_start = (now - ev.start) / pd.Timedelta(days=1)
        last = acct.state.get("last_buy_attempt_ts")
        due = last is None or (now - pd.Timestamp(last)) >= pd.Timedelta(minutes=self.buy_every) - pd.Timedelta(seconds=90)
        if due and since_start >= self.start_after_days and days_left > 0.01:
            acct.state["last_buy_attempt_ts"] = now.isoformat()
            self._try_buy(ev, now, preds, quotes, self.buy_block_reason(now, poly, local))
        elif not due:
            nxt = pd.Timestamp(last) + pd.Timedelta(minutes=self.buy_every)
            self.con.say(f"\n  (next hourly buy decision at ~{nxt.tz_convert('US/Eastern'):%H:%M} ET)")
        elif since_start < self.start_after_days:
            self.con.say(f"\n  (buying starts {self.start_after_days} days after the market opens)")
        acct.save()

        # ---- equity, charts
        qk = {self._key(ev.slug, t): q for t, q in quotes.items()}
        fees = {self._key(ev.slug, b.title): b.fees for b in ev.buckets}
        eq = acct.equity(qk, fees)
        acct.log_equity(now, ev.slug, self.tweets, eq)
        held = {p["bucket"] for p in acct.positions.values() if p["event"] == ev.slug}
        if self.ticks % self.chart_every == 0:
            plot_market(self.run_dir, f"{ev.title}  |  {now.tz_convert('US/Eastern'):%a %b %d %H:%M} ET  |  {days_left:.2f} days left",
                        titles, preds, quotes, held, rules, self.tweets)
            plot_equity(self.run_dir, acct.state["start_cash"])
            self._archive_charts(now)
        write_summary(self.run_dir, acct.state, {"event": ev.slug, "tweets so far": self.tweets,
                                                 "equity (conservative)": f"${eq['equity_conservative']:.2f}",
                                                 "last tick": now.isoformat(timespec="seconds"), "prediction source": self.model.name})
        log.info("tick: cash $%.2f | equity $%.2f | %d open | tweets %s | %.2f d left", acct.cash, eq["equity_conservative"],
                 len(acct.positions), self.tweets, days_left)
        self._show_account(eq, now)
        self.ticks += 1

    # ------------------------------------------------------------------ console blocks
    def _show_tweet_check(self, poly, local, newest, n_quotes, n_buckets):
        c = self.con
        c.section("TWEET COUNT CHECK")
        c.say(f"  Polymarket page (resolution source) : {poly if poly is not None else 'UNAVAILABLE'}")
        c.say(f"  Our own tweet database              : {local}    (newest tweet in it: {newest})")
        if poly is not None and local is not None:
            d = poly - local
            c.say("  -> MATCH: both sources agree" if d == 0 else
                  f"  -> difference {d:+d}: {'XTracker has newer tweets than our database (refreshed hourly)' if d > 0 else 'our database is ahead of the page'}")
        c.say(f"  Order books fetched                 : {n_quotes}/{n_buckets}")

    def _held_map(self, ev):
        return {p["bucket"]: p for p in self.account.positions.values() if p["event"] == ev.slug}

    def _show_market(self, ev, titles, preds, quotes, days_left):
        c, rules = self.con, self.rules
        if not c.enabled:
            return
        cands = {x["bucket"] for x in buy_candidates(preds, quotes, rules)}
        held = self._held_map(ev)
        c.section(f"MARKET vs OUR MODEL   (tweets so far {self.tweets}, {days_left:.2f} days left, model: {self.model.name})")
        c.say(f"  {'Bucket':>9s} {'Ours':>7s} {'Mkt mid':>8s} {'Bid':>7s} {'Ask':>7s} {'Edge':>8s} {'Held sh':>8s}   Signal")
        for t in titles:
            q = quotes.get(t)
            bid = q.best_bid if q else None
            ask = q.best_ask if q else None
            ours = preds.get(t, 0.0)
            if not (ours >= 0.005 or (ask is not None and ask >= 0.01) or t in held):
                continue
            mid = (bid + ask) / 2 if bid is not None and ask is not None else None
            edge = (ours - ask) * 100 if ask is not None else None
            sig = ""
            if t in cands:
                sig = "BUY candidate (meets all 3 rules)"
            elif t in held:
                rsn = sell_reason(ours, bid, rules)
                sig = f"SELL ({rsn})" if rsn else "held"
            f = lambda v: f"{v * 100:6.1f}%" if v is not None else "     - "
            c.say(f"  {t:>9s} {ours * 100:6.1f}% {f(mid):>8s} {f(bid):>7s} {f(ask):>7s} {('%+6.1fpt' % edge) if edge is not None else '      -':>8s} "
                  f"{held[t]['shares'] if t in held else 0:8.2f}   {sig}")
        if held:
            c.section("OPEN POSITIONS")
            c.say(f"  {'Bucket':>9s} {'Shares':>8s} {'Cost $':>8s} {'Avg cost':>9s} {'Bid':>7s} {'Value@bid':>10s} {'Unreal. P&L':>12s} {'Ours':>7s}")
            for t, pos in held.items():
                q = quotes.get(t)
                bid = q.best_bid if q else None
                b = self._bucket(ev, t)
                val = (pos["shares"] * bid - taker_fee(pos["shares"], bid, b.fees)) if bid is not None and b else pos["cost_usd"]
                c.say(f"  {t:>9s} {pos['shares']:8.2f} {pos['cost_usd']:8.2f} {pos['cost_usd'] / pos['shares'] * 100:8.1f}% "
                      f"{(bid * 100 if bid is not None else float('nan')):6.1f}% {val:10.2f} {val - pos['cost_usd']:+12.2f} {preds.get(t, 0) * 100:6.1f}%")
            c.say("  (value = shares x best bid minus the taker fee for selling them)")

    def _explain_misses(self, preds, quotes, n=4):
        rules = self.rules
        rows = sorted(((p - quotes[b].best_ask, b, p, quotes[b].best_ask) for b, p in preds.items()
                       if b in quotes and quotes[b].best_ask is not None), reverse=True)[:n]
        for edge, b, p, ask in rows:
            ok = lambda cond: "ok" if cond else "FAILS"
            self.con.say(f"     {b:>9s}   ours {p * 100:5.1f}% [{ok(p >= rules.min_pred)} >= {rules.min_pred * 100:.0f}%]   ask {ask * 100:5.1f}% [{ok(ask >= rules.min_mkt)} >= {rules.min_mkt * 100:.0f}%]"
                         f"   edge {edge * 100:+5.1f}pt [{ok(edge > rules.min_edge + 1e-12)} > {rules.min_edge * 100:.1f}pt]")

    def _show_account(self, eq, now):
        a, c = self.account, self.con
        start = a.state["start_cash"]
        c.section("ACCOUNT")
        c.say(f"  cash ${a.cash:.2f} | open positions (at bid, net of sell fee) ${eq['positions_bid_value']:.2f} | EQUITY ${eq['equity_conservative']:.2f} "
              f"({(eq['equity_conservative'] / start - 1) * 100:+.1f}% vs start ${start:.2f})")
        c.say(f"  realised P&L {a.state['realized_pnl']:+.2f} | fees paid ${a.state['fees_paid']:.4f} | buys {a.state['n_buys']} | sells {a.state['n_sells']} | settled {a.state['n_settled']}")
        if self.feed.mode == "live":
            step = self.sell_every * 60
            nxt = (now + pd.Timedelta(seconds=step - (now.timestamp() % step))).round("min")
            c.say(f"  next tick ~{nxt.tz_convert('US/Eastern'):%H:%M} ET | charts: equity.png market.png | logs: paper_trader.log console.log")

    def startup_banner(self):
        c, ev, r = self.con, self.event, self.rules
        fs = ev.buckets[0].fees if ev and ev.buckets else None
        c.banner("POLYMARKET PAPER TRADER - STARTING (no real orders are ever sent)")
        c.say(f"  run folder      : {self.run_dir}")
        c.say(f"  market          : {ev.title}")
        c.say(f"                    {ev.start} -> {ev.end}   ({ev.slug})")
        c.say(f"  bankroll        : start ${self.account.state['start_cash']:.2f}, cash now ${self.account.cash:.2f}, {len(self.account.positions)} open positions (state is resumed if the folder existed)")
        c.say(f"  BUY             : ${r.stake:.2f} (fee included) every {self.buy_every} min, from {self.start_after_days} days after a market opens")
        c.say(f"                    candidates: our prob >= {r.min_pred * 100:.0f}%, market ask >= {r.min_mkt * 100:.0f}%, our prob > ask + {r.min_edge * 100:.1f}pt; one drawn at random (weight = edge)")
        c.say(f"  SELL            : checked every {self.sell_every} min, whole position at the bid when our prob < {r.sell_below * 100:.0f}%"
              + (" or market bid > our prob" if r.sell_if_bid_above_pred else ""))
        c.say(f"  FEES            : taker fee = shares x {fs.rate} x price x (1-price) on every buy and sell (read from the market's own feeSchedule)" if fs else "  FEES            : none")
        c.say(f"  PREDICTIONS     : {self.model.name} (ensemble re-run every {self.model_refresh} min in a separate process)")
        c.say("  DATA            : Polymarket order books + tweet count every tick; XTracker tweet export merged hourly")
        c.say("  FILES           : console.log (this screen), paper_trader.log, trades.csv, decisions.csv, snapshots.csv, equity.csv, data_log.csv, forecasts.csv, model_logs/")
        c.say("  stop with Ctrl-C; run the same command again to resume")

    def _write_snapshot(self, ev, now, titles, preds, quotes, days_left):
        """Every bucket, every tick: our probability, best bid/ask, top-5 depth, what we hold. For analysis after the run."""
        path = os.path.join(self.run_dir, "snapshots.csv")
        new = not os.path.exists(path)
        held = {p["bucket"]: p["shares"] for p in self.account.positions.values() if p["event"] == ev.slug}
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=SNAPSHOT_FIELDS)
            if new:
                w.writeheader()
            for t in titles:
                q = quotes.get(t)
                bids = sorted(q.bids, reverse=True)[:5] if q else []
                asks = sorted(q.asks)[:5] if q else []
                w.writerow({"ts": now.isoformat(timespec="seconds"), "event": ev.slug, "bucket": t,
                            "our_prob": round(preds.get(t, 0.0), 6),
                            "bid": bids[0][0] if bids else "", "ask": asks[0][0] if asks else "",
                            "bid_size_best": bids[0][1] if bids else "", "ask_size_best": asks[0][1] if asks else "",
                            "bid_depth_top5": round(sum(p * z for p, z in bids), 2), "ask_depth_top5": round(sum(p * z for p, z in asks), 2),
                            "held_shares": held.get(t, 0.0), "tweets": self.tweets, "days_left": round(days_left, 4)})

    def _archive_charts(self, now):
        """Keep an hourly copy of both charts (the main ones are overwritten every tick)."""
        stamp = now.strftime("%Y%m%d_%H%M")
        hour = stamp[:11]
        if getattr(self, "_last_archive_hour", None) == hour:
            return
        self._last_archive_hour = hour
        d = os.path.join(self.run_dir, "charts_archive")
        os.makedirs(d, exist_ok=True)
        for name in ("market.png", "equity.png"):
            src = os.path.join(self.run_dir, name)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(d, f"{name[:-4]}_{stamp}.png"))

    def _try_buy(self, ev: Event, now, preds, quotes, blocked: Optional[str] = None):
        acct, rules = self.account, self.rules
        cands = buy_candidates(preds, quotes, rules)
        chosen = choose_buy(cands, self.rng)
        row = {"ts": now.isoformat(timespec="seconds"), "event": ev.slug, "tweets": self.tweets, "days_left": round(ev.days_left(now), 3),
               "cash": round(acct.cash, 4), "n_candidates": len(cands),
               "candidates": json.dumps([{k: round(v, 4) if isinstance(v, float) else v for k, v in c.items()} for c in cands])}
        self.con.section("BUY DECISION (hourly)")
        self.con.say(f"  rules: our prob >= {rules.min_pred * 100:.0f}%  AND  market ask >= {rules.min_mkt * 100:.0f}%  AND  our prob > ask + {rules.min_edge * 100:.1f}pt"
                     f"   -> one bucket drawn at random (weight = edge), ${rules.stake:.2f} per buy")
        if cands:
            self.con.say(f"  {len(cands)} bucket(s) qualify:")
            wsum = sum(c["edge"] for c in cands)
            for c in sorted(cands, key=lambda c: -c["edge"]):
                self.con.say(f"     {c['bucket']:>9s}   ours {c['pred'] * 100:5.1f}%   ask {c['ask'] * 100:5.1f}%   edge {c['edge'] * 100:+5.1f}pt   draw probability {c['edge'] / wsum:.2f}")
        else:
            self.con.say("  no bucket qualifies. Closest ones and the rule they fail:")
            self._explain_misses(preds, quotes)
        if blocked:
            row["result"] = f"blocked: {blocked}"
            log.warning("new entries blocked: %s", blocked)
            self.con.say(f"  -> NO BUY: {blocked}")
        elif acct.cash < rules.stake - 1e-9:
            row["result"] = "skipped: not enough cash"
            self.con.say(f"  -> skipped: cash ${acct.cash:.2f} is below the ${rules.stake:.2f} stake")
        elif chosen is None:
            row["result"] = "no candidate"
            self.con.say("  -> NO BUY this hour")
        else:
            b = self._bucket(ev, chosen["bucket"])
            q = quotes[chosen["bucket"]]
            fill = buy_with_budget(q.asks, rules.stake, b.fees, max_avg_price=chosen["ask"] + self.max_slippage)
            if fill is None:
                row["result"] = "order not filled (depth/slippage)"
                self.con.say(f"  -> drew {chosen['bucket']} but the order could not be filled within {self.max_slippage * 100:.1f}pt of the best ask")
            else:
                acct.buy(self._key(ev.slug, b.title), ev.slug, b.title, b.token, fill, now,
                         {"pred": round(chosen["pred"], 5), "ask": chosen["ask"], "bid": q.best_bid, "reason": "buy rule",
                          "draw_prob": round(chosen["draw_prob"], 4), "n_candidates": chosen["n_candidates"]})
                row.update({"result": f"BOUGHT {fill.shares:.2f} sh @ {fill.avg_price:.4f} fee {fill.fee:.4f}", "chosen": b.title,
                            "pred": round(chosen["pred"], 4), "ask": chosen["ask"], "edge": round(chosen["edge"], 4),
                            "draw_prob": round(chosen["draw_prob"], 4)})
                log.info("BUY %s: %.2f sh @ %.3f (ours %.1f%% vs ask %.1f%%, drawn with p=%.2f of %d candidates), fee %.4f",
                         b.title, fill.shares, fill.avg_price, chosen["pred"] * 100, chosen["ask"] * 100, chosen["draw_prob"], len(cands), fill.fee)
                self.con.say("")
                self.con.say(f"  SELECTED BUY OPPORTUNITY: {b.title}   (drawn with probability {chosen['draw_prob']:.2f} among {len(cands)})")
                self.con.say(f"     our probability {chosen['pred'] * 100:.1f}%  vs market ask {chosen['ask'] * 100:.1f}%  -> edge {chosen['edge'] * 100:+.1f}pt")
                self.con.say(f"     ORDER: bought {fill.shares:.2f} shares at an average {fill.avg_price * 100:.2f}%  ({fill.levels_used} book level(s))")
                self.con.say(f"     cost ${fill.notional:.4f} + taker fee ${fill.fee:.4f} = ${-fill.cash_delta:.4f}   | cash now ${acct.cash:.2f}")
                self.con.say(f"     a winning share pays $1 -> this position pays ${fill.shares:.2f} if {b.title} is the final bucket, else $0")
        append_csv(os.path.join(self.run_dir, "decisions.csv"), DECISION_FIELDS, row)

    def _log_equity_only(self, now, quotes=None):
        eq = self.account.equity({}, {})
        self.account.log_equity(now, self.event.slug if self.event else "", self.tweets, eq)
        plot_equity(self.run_dir, self.account.state["start_cash"])

    # ------------------------------------------------------------------ live loop
    def _sleep_until(self, deadline: float):
        """Sleep in <=5 s slices until the monotonic `deadline`. The remaining time is recomputed at the call, so a
        wall-clock jump or a machine suspend can never hand time.sleep() a negative number (B01)."""
        while not self._stop:
            remaining = deadline - self._mono()
            if remaining <= 0:
                return
            self._sleep(min(5.0, remaining))
            if self._mono() - self._last_beat >= 60:
                self._beat()

    def _beat(self, **extra):
        self._last_beat = self._mono()
        write_heartbeat(self.run_dir, ticks=self.ticks, stop=self._stop, fails=self._fails, **extra)

    def run_live(self):
        log.info("paper trading LIVE | run dir %s | rules %s", self.run_dir, self.rules.as_dict())
        self.startup_banner()
        step = self.sell_every * 60
        self._fails = 0
        while not self._stop:
            try:
                self.tick(pd.Timestamp.now(tz="UTC"))
                self._fails = 0
            except Exception:
                self._fails += 1
                log.error("tick failed (%d in a row):\n%s", self._fails, traceback.format_exc())
            self._beat(last_tick_ok=self._fails == 0)
            sleep_for = max(0.0, step - (self._wall() % step))          # align to the 10-minute clock
            if self._fails >= 3:
                sleep_for = max(sleep_for, 120)
            self._sleep_until(self._mono() + sleep_for)
        log.info("stopped; state saved")

    def stop(self, *_):
        self._stop = True

    # ------------------------------------------------------------------ replay
    def run_replay(self, slug: str):
        ev = self.feed.load_event(slug)
        self.event = ev
        self.events[slug] = ev
        self.auto_roll = False
        grid = self.feed.grid(ev)
        log.info("REPLAY %s: %d ticks of %d min", slug, len(grid), self.sell_every)
        for i, now in enumerate(grid):
            self.tick(now)
        # market over -> settle
        end = ev.end + pd.Timedelta(minutes=1)
        self._settle_finished(end)
        self.account.log_equity(end, slug, self.tweets, self.account.equity({}, {}))   # final point, after settlement
        plot_equity(self.run_dir, self.account.state["start_cash"])
        write_summary(self.run_dir, self.account.state, {"event": slug, "mode": "replay"})
        return self.account.state


class UtcFormatter(logging.Formatter):
    """ISO-8601 UTC with an explicit offset, so log age never depends on the host timezone (B16)."""
    converter = time.gmtime

    def formatTime(self, record, datefmt=None):
        return time.strftime("%Y-%m-%dT%H:%M:%S", self.converter(record.created)) + f",{int(record.msecs):03d}+00:00"


def _same_file(stream, path) -> bool:
    try:
        return os.path.exists(path) and os.path.samestat(os.fstat(stream.fileno()), os.stat(path))
    except Exception:
        return False


def configure_logging(run_dir: str, mirror_console: bool = False):
    """Handlers: stderr (the supervisor's journal), paper_trader.log (complete), and with mirror_console the
    console.log mirror. console.log has ONE writer: this process. Do not also `tee` stdout/stderr into it (B15);
    if stderr/stdout was redirected straight onto console.log the mirror is skipped so lines are not doubled."""
    os.makedirs(run_dir, exist_ok=True)
    fmt = UtcFormatter("%(asctime)s %(levelname)s %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    fh = logging.FileHandler(os.path.join(run_dir, "paper_trader.log"), mode="a")      # append forever: nothing is rotated or deleted
    fh.setFormatter(fmt)
    root.addHandler(sh)
    root.addHandler(fh)
    console_path = os.path.join(run_dir, "console.log")
    if mirror_console and not (_same_file(sys.stderr, console_path) or _same_file(sys.stdout, console_path)):
        ch = logging.FileHandler(console_path, mode="a")
        ch.setFormatter(fmt)
        root.addHandler(ch)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
