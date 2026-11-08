"""Regression tests for the B01-B17 audit (live40, Nov 2-6). Each one reproduces the incident shape."""
import csv
import json
import logging
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import pytest

from src.simulation.paper_trader.feeds import Bucket, Event
from src.simulation.paper_trader.fills import FeeSchedule as FEES_T
from src.simulation.paper_trader.procutil import AlreadyRunning, RunLock, lock_state
from src.simulation.paper_trader.runner import PaperTrader, UtcFormatter, configure_logging
from src.simulation.paper_trader.strategy import Quote, Rules
from test_paper_trader import FakeFeed, make_event

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def make_trader(tmp_path, **kw):
    ev = make_event()
    t = PaperTrader(FakeFeed(), Rules(), str(tmp_path), kw.pop("bankroll", 30.0), buy_every_min=60, sell_every_min=10, b=1.0,
                    start_after_days=0, chart_every=1000, **kw)
    t.event, t.events["fake"] = ev, ev
    return t, ev


# ---------------------------------------------------------------- B01 negative sleep
class Clock:
    """Fake monotonic clock; `sleep` advances it and records every requested duration."""
    def __init__(self):
        self.now, self.sleeps = 1000.0, []

    def mono(self):
        return self.now

    def sleep(self, s):
        if s < 0:
            raise ValueError("sleep length must be non-negative")      # exactly what time.sleep does
        self.sleeps.append(s)
        self.now += s


def test_sleep_until_never_negative_even_when_deadline_passes_between_check_and_call(tmp_path):
    t, _ = make_trader(tmp_path)
    c = Clock()
    t._mono, t._sleep = c.mono, c.sleep
    t._sleep_until(c.now + 0.01)                 # tiny interval
    t._sleep_until(c.now)                        # zero
    t._sleep_until(c.now - 5)                    # already in the past (clock jumped / machine resumed)
    t._sleep_until(c.now + 12)
    assert all(s >= 0 for s in c.sleeps)
    assert c.sleeps[:1] == [pytest.approx(0.01)] and max(c.sleeps) <= 5.0


def test_run_live_survives_wall_clock_jump_and_tick_failures(tmp_path, monkeypatch):
    t, _ = make_trader(tmp_path)
    c = Clock()
    t._mono, t._sleep = c.mono, c.sleep
    import itertools
    wall = itertools.cycle([-5e9, 1e12, 7.0, 600.0, 1.23e9])          # backwards / huge jumps
    t._wall = lambda: next(wall)
    calls = {"n": 0}

    def boom(now):
        calls["n"] += 1
        if calls["n"] >= 4:
            t.stop()
        raise RuntimeError("tick blew up")                  # three+ consecutive failures
    t.tick = boom
    t.run_live()                                            # must return normally, not raise ValueError
    assert calls["n"] == 4 and all(s >= 0 for s in c.sleeps)
    assert t._fails >= 3 and max(c.sleeps) <= 5.0
    hb = json.load(open(tmp_path / "heartbeat.json"))
    assert hb["fails"] >= 3


def test_stop_interrupts_sleep(tmp_path):
    t, _ = make_trader(tmp_path)
    c = Clock()
    t._mono = c.mono

    def sleep_and_stop(s):
        c.sleep(s)
        t.stop()
    t._sleep = sleep_and_stop
    t._sleep_until(c.now + 600)
    assert len(c.sleeps) == 1


# ---------------------------------------------------------------- B02 fatal exit diagnostics
def test_uncaught_exception_leaves_traceback_and_exit_status(tmp_path, monkeypatch):
    from src.simulation.paper_trader import __main__ as m

    def explode(argv=None):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(m, "_main", explode)
    code = m.main(["--run-name", "x", "--runs-dir", str(tmp_path)])
    assert code == 1
    st = json.load(open(tmp_path / "x" / "exit_status.json"))
    assert st["reason"] == "uncaught exception" and "kaboom" in st["traceback"] and st["exit_code"] == 1


# ---------------------------------------------------------------- B14 singleton lock
def test_only_one_process_can_own_the_run(tmp_path):
    path = str(tmp_path / "run.lock")
    code = ("import sys,time;sys.path.insert(0,%r);from src.simulation.paper_trader.procutil import RunLock;"
            "l=RunLock(%r).acquire();print('locked',flush=True);time.sleep(30)" % (ROOT, path))
    child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True, cwd=ROOT)
    try:
        assert child.stdout.readline().strip() == "locked"
        assert lock_state(path)[0] == "held"
        with pytest.raises(AlreadyRunning):
            RunLock(path).acquire()
        child.kill()                                       # kill -9: the kernel drops the lock, no stale PID file to adopt
        child.wait()
        assert lock_state(path)[0] == "free"
        with RunLock(path):                                # restart adopts it
            assert lock_state(path)[0] == "held"
    finally:
        child.kill()


def test_pid_reuse_cannot_fake_liveness(tmp_path):
    p = tmp_path / "run.lock"
    p.write_text(json.dumps({"pid": os.getpid()}))        # lock file names a live PID (ours) but nobody holds the lock
    assert lock_state(str(p))[0] == "free"


def test_status_uses_lock_not_pid(tmp_path):
    from src.simulation.paper_trader.status import check
    (tmp_path / "run.lock").write_text(json.dumps({"pid": os.getpid()}))
    level, lines = check(str(tmp_path))
    assert level == 2 and any("no process holds it" in m for _, m in lines)
    with RunLock(str(tmp_path / "run.lock")):
        level, lines = check(str(tmp_path))
        assert any("process running" in m for _, m in lines)


# ---------------------------------------------------------------- B15 duplicated logger output
def test_console_lines_appear_exactly_once(tmp_path):
    configure_logging(str(tmp_path), mirror_console=True)
    from src.simulation.paper_trader.console import Console
    con = Console(str(tmp_path), True)
    con.banner("BANNER-ONCE")
    con.say("SAY-ONCE")
    logging.getLogger("paper_trader").info("LOG-ONCE")
    text = open(tmp_path / "console.log").read()
    assert text.count("BANNER-ONCE") == 1 and text.count("SAY-ONCE") == 1 and text.count("LOG-ONCE") == 1
    assert open(tmp_path / "paper_trader.log").read().count("LOG-ONCE") == 1


def test_mirror_skipped_when_stderr_already_is_console_log(tmp_path, monkeypatch):
    f = open(tmp_path / "console.log", "a")
    monkeypatch.setattr(sys, "stderr", f)
    configure_logging(str(tmp_path), mirror_console=True)
    logging.getLogger("paper_trader").info("ONCE-ONLY")
    f.flush()
    assert open(tmp_path / "console.log").read().count("ONCE-ONLY") == 1


# ---------------------------------------------------------------- B16 timezone independence
@pytest.mark.parametrize("tz", ["UTC", "Asia/Tbilisi", "America/New_York"])
def test_status_log_age_is_timezone_independent(tmp_path, tz, monkeypatch):
    from src.simulation.paper_trader import status
    monkeypatch.setenv("TZ", tz)
    time.tzset()
    try:
        now = pd.Timestamp.now(tz="UTC")
        rec = logging.LogRecord("x", logging.ERROR, "", 0, "boom", None, None)
        rec.created = now.timestamp() - 120
        line = UtcFormatter("%(asctime)s %(levelname)s %(message)s").format(rec)
        (tmp_path / "paper_trader.log").write_text(line + "\n")
        assert line.split(" ")[0].endswith("+00:00")
        level, lines = status.check(str(tmp_path))
        assert any("1 errors" in m for _, m in lines), (tz, lines)
        # a legacy naive stamp 2h old (host-local) must be outside the 60 min window in every timezone
        old = (pd.Timestamp.now() - pd.Timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S,000")
        (tmp_path / "paper_trader.log").write_text(f"{old} ERROR old\n")
        level, lines = status.check(str(tmp_path))
        assert any("0 errors" in m for _, m in lines), (tz, lines)
    finally:
        monkeypatch.delenv("TZ")
        time.tzset()


# ================================================================ B04 / B05 tweet download + parser
GOOD_EXPORT = ('id,text,created_at\n'
               '1874324392051957998,"HNY LFG 2025!!!","Jan 1, 12:18:52 AM EST"\n'
               '1874330909589356693,"https://t.co/uON7cFPXnf","Jan 1, 12:44:46 AM EST"\n')


def test_validate_export_rejects_bad_downloads(tmp_path):
    sys.path.insert(0, ROOT)
    from src.xpath_scraper.TweetCSVGetter import ExportInvalid, validate_export
    p = tmp_path / "e.csv"
    with pytest.raises(ExportInvalid):
        validate_export(str(p))                                         # missing
    p.write_text("")
    with pytest.raises(ExportInvalid):
        validate_export(str(p))                                         # empty
    p.write_text("<!DOCTYPE html><html><body>Application Error</body></html>")
    with pytest.raises(ExportInvalid):
        validate_export(str(p))                                         # Heroku page served with HTTP 200
    p.write_text("a,b,c\n1,2,3\n")
    with pytest.raises(ExportInvalid):
        validate_export(str(p))                                         # wrong schema
    p.write_text("id,text,created_at\n")
    with pytest.raises(ExportInvalid):
        validate_export(str(p))                                         # header only
    p.write_text(GOOD_EXPORT)
    assert validate_export(str(p)) == 2


def run_formatter(tmp_path):
    env = dict(os.environ, TWEET_TEMP_DIR=str(tmp_path))
    return subprocess.run([sys.executable, os.path.join(ROOT, "src/formating_tweet_data/secondFixDates.py")], env=env,
                          capture_output=True, text=True, cwd=ROOT)


def test_formatter_exit_codes(tmp_path):
    r = run_formatter(tmp_path)                                         # missing input
    assert r.returncode != 0
    (tmp_path / "elonmusk.csv").write_text(GOOD_EXPORT)
    r = run_formatter(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    out = (tmp_path / "elonmusk_reformatted.csv").read_text()
    assert "2025:01:01:00:18:52" in out
    (tmp_path / "elonmusk.csv").write_text(GOOD_EXPORT + '1874341547917140387,"bad date row","not a date"\n')
    r = run_formatter(tmp_path)                                         # unparseable date -> nonzero, no partial output
    assert r.returncode != 0 and not (tmp_path / "elonmusk_reformatted.csv").exists()
    (tmp_path / "elonmusk.csv").write_text("id,text,created_at\n")
    assert run_formatter(tmp_path).returncode != 0                     # no rows at all


def _combiner():
    sys.path.insert(0, os.path.join(ROOT, "src", "xpath_scraper"))
    import combiner
    return combiner


T1 = '"1","a","2026:11:01:10:00:00"\n'
T2 = '"2","b","2026:11:01:11:00:00"\n'
T3 = '"3","c","2026:11:01:12:00:00"\n'
HDR = '"id","text","created_at"\n'


def test_merge_adds_new_rows_and_reports_result(tmp_path):
    c = _combiner()
    (tmp_path / "t.csv").write_text(HDR + T1 + T2)
    (tmp_path / "s.csv").write_text(HDR + T2 + T3)
    res = c.merge_files(str(tmp_path / "s.csv"), str(tmp_path / "t.csv"))
    assert res["new_rows"] == 1 and res["total_rows"] == 3 and res["newest"] == "2026:11:01:12:00:00" and len(res["sha256"]) == 64
    assert (tmp_path / "t.csv").read_text() == HDR + T1 + T2 + T3


@pytest.mark.parametrize("source,target", [
    (HDR + T3 + 'garbage line\n', HDR + T1 + T2),                       # unparseable line in source
    (HDR + T3, HDR + T1 + '"2","b","2026-99-99"\n'),                    # target line the rewrite would silently drop
    (HDR, HDR + T1),                                                    # empty source
])
def test_merge_refuses_and_leaves_target_untouched(tmp_path, source, target):
    c = _combiner()
    (tmp_path / "t.csv").write_text(target)
    (tmp_path / "s.csv").write_text(source)
    with pytest.raises(RuntimeError):
        c.merge_files(str(tmp_path / "s.csv"), str(tmp_path / "t.csv"))
    assert (tmp_path / "t.csv").read_text() == target
    with pytest.raises(RuntimeError):                                   # missing source file
        c.merge_files(str(tmp_path / "nope.csv"), str(tmp_path / "t.csv"))


def _fake_run(stdout="", stderr="", rc=0, calls=None):
    def run(cmd, **kw):
        if calls is not None:
            calls.append(cmd)
        return subprocess.CompletedProcess(cmd, rc, stdout, stderr)
    return run


def test_refresh_exit0_without_result_is_a_failure(monkeypatch):
    from src.simulation.paper_trader import feeds
    f = feeds.LiveFeed()
    monkeypatch.setattr(feeds.subprocess, "run", _fake_run(stdout="all good\n"))
    assert f.refresh_tweet_data()["ok"] is False
    monkeypatch.setattr(feeds.subprocess, "run", _fake_run(stdout='REFRESH_RESULT {"new_rows": 5, "total_rows": 9, "newest": "x", "sha256": "h"}'))
    r = f.refresh_tweet_data()
    assert r["ok"] and r["new_tweets"] == 5
    monkeypatch.setattr(feeds.subprocess, "run", _fake_run(stderr="boom", rc=1))
    assert f.refresh_tweet_data()["ok"] is False


def test_failed_refresh_fails_the_forecast_without_running_the_model(monkeypatch, tmp_path):
    from src.simulation.paper_trader import feeds
    calls = []
    monkeypatch.setattr(feeds.subprocess, "run", _fake_run(stderr="503", rc=1, calls=calls))
    fc = feeds.LiveFeed().forecast(make_event(), pd.Timestamp("2026-11-03 12:00", tz="UTC"), str(tmp_path))
    assert fc is None
    assert len(calls) == 1 and "TweetCSVGetter" in " ".join(calls[0])      # model_worker was never launched


# ================================================================ B06 / B07 / B08 forecast lifecycle
from src.simulation.paper_trader.model import (ForecastError, NativeEnsembleModel, gamma_bucket_probs, map_native_frames,
                                               validate_forecast, CalibratedModel)

GOOD = {"total_predicted": 420.0, "current_tweets": 300, "time_remaining_days": 2.0, "frames": None}


@pytest.mark.parametrize("bad", [
    {**GOOD, "total_predicted": 250.0},                      # total below tweets already counted
    {**GOOD, "time_remaining_days": 0.0},                    # zero horizon
    {**GOOD, "time_remaining_days": -1.0},
    {**GOOD, "total_predicted": float("nan")},
    {**GOOD, "total_predicted": float("inf")},
    {**GOOD, "total_predicted": -5.0},
    {**GOOD, "current_tweets": None},
    {**GOOD, "event_slug": "some-old-event"},
    {**GOOD, "generated_at_utc": "2999-01-01T00:00:00+00:00"},   # from the future
    "not a dict",
])
def test_bad_forecasts_rejected_and_never_make_model_ready(tmp_path, bad):
    t, ev = make_trader(tmp_path)
    now = ev.start + pd.Timedelta(days=5)
    with pytest.raises(ForecastError):
        t._apply_forecast(bad, ev, now)
    assert not t.model.ready and not os.path.exists(tmp_path / "forecast_state.json")


def test_bad_forecast_does_not_replace_a_good_one(tmp_path):
    t, ev = make_trader(tmp_path)
    now = ev.start + pd.Timedelta(days=5)
    t._apply_forecast(GOOD, ev, now)
    rate = t.model.rate
    with pytest.raises(ForecastError):
        t._apply_forecast({**GOOD, "total_predicted": 100.0}, ev, now)
    assert t.model.ready and t.model.rate == rate


def test_probability_functions_fail_closed():
    rng = [(i, i + 19) for i in range(0, 600, 20)]
    for kw in (dict(so_far=float("nan")), dict(rate_per_day=-1.0), dict(days_left=float("inf")), dict(days_left=-1)):
        args = dict(so_far=300, rate_per_day=60, days_left=2.0)
        args.update(kw)
        with pytest.raises(ForecastError):
            gamma_bucket_probs(rng, **args)
    with pytest.raises(ForecastError):
        gamma_bucket_probs([(0, 19), (20, 39)], so_far=500, rate_per_day=10, days_left=1)      # count outside every bucket
    p = gamma_bucket_probs(rng, so_far=305, rate_per_day=60, days_left=0.0)                   # zero horizon: stays put
    assert p[15] == pytest.approx(1.0)                                                         # bucket 300-319, no invented tweets
    p0 = gamma_bucket_probs(rng, so_far=305, rate_per_day=0.0, days_left=3.0)
    assert p0[15] == pytest.approx(1.0)
    # native frames: impossible outcomes zeroed, zero mass rejected (no uniform fallback)
    nat = map_native_frames({"0-19": 0.5, "20-39": 0.5}, [(0, 19), (20, 39)], so_far=25)
    assert nat.tolist() == [0.0, 1.0]
    with pytest.raises(ForecastError):
        map_native_frames({"0-19": 1.0}, [(0, 19), (20, 39)], so_far=25)
    with pytest.raises(ForecastError):
        map_native_frames({"900-919": 1.0}, [(0, 19), (20, 39)])


def test_restart_restores_forecast_and_keeps_selling(tmp_path):
    t, ev = make_trader(tmp_path)
    now = ev.start + pd.Timedelta(days=5)
    t._apply_forecast(GOOD, ev, now)
    t.tick(now)
    held_before = len(t.account.positions)
    # "restart": brand-new trader on the same run dir, worker will fail from now on
    class Failing(FakeFeed):
        def forecast(self, *a, **k):
            return None
    t2 = PaperTrader(Failing(), Rules(), str(tmp_path), 30.0, b=1.0, start_after_days=0, chart_every=1000)
    t2.event, t2.events["fake"] = ev, ev
    later = now + pd.Timedelta(minutes=10)
    t2._refresh_model(ev, later, blocking=False)
    assert t2.model.ready and t2.model_age_min(later) == pytest.approx(10.0)         # true age, not attempt time
    assert t2.buy_block_reason(later, 300, 300) is None
    # a held position whose bid exceeds our probability is still sold although the next worker run fails
    if t2.account.positions:
        bucket = next(iter(t2.account.positions.values()))["bucket"]
        t2.feed.books[bucket] = Quote([(0.95, 500)], [(0.97, 500)])
    n_sells = t2.account.state["n_sells"]
    t2.tick(later)
    assert held_before == 0 or t2.account.state["n_sells"] == n_sells + 1


@pytest.mark.parametrize("mutate", ["expired", "corrupt", "wrong_event", "wrong_schema", "bad_values"])
def test_invalid_saved_forecast_never_becomes_ready(tmp_path, mutate):
    t, ev = make_trader(tmp_path)
    now = ev.start + pd.Timedelta(days=5)
    t._apply_forecast(GOOD, ev, now)
    path = tmp_path / "forecast_state.json"
    st = json.loads(path.read_text())
    later = now + pd.Timedelta(minutes=10)
    if mutate == "expired":
        later = now + pd.Timedelta(minutes=151)
    elif mutate == "corrupt":
        path.write_text(path.read_text()[:40])
    elif mutate == "wrong_event":
        st["event_slug"] = "other"
    elif mutate == "wrong_schema":
        st["schema"] = 99
    elif mutate == "bad_values":
        st["forecast"]["total_predicted"] = 1.0
    if mutate not in ("expired", "corrupt"):
        path.write_text(json.dumps(st))
    t2 = PaperTrader(FakeFeed(), Rules(), str(tmp_path), 30.0, b=1.0, chart_every=1000)
    assert t2._restore_forecast(ev, later) is False and not t2.model.ready


class CountingFeed(FakeFeed):
    mode = "live"

    def __init__(self, ok=False):
        super().__init__()
        self.calls, self.ok = 0, ok
        import threading
        self.release = threading.Event()

    def forecast(self, event, now, out_dir="", seed=42):
        self.calls += 1
        self.release.wait(5)
        return dict(GOOD) if self.ok else None


def _join(t):
    if t._forecast_thread is not None:
        t._forecast_thread.join(5)


def test_one_job_in_flight_and_exponential_backoff(tmp_path):
    feed = CountingFeed(ok=False)
    t = PaperTrader(feed, Rules(), str(tmp_path), 30.0, b=1.0, chart_every=1000)
    ev = make_event()
    now = ev.start + pd.Timedelta(days=5)
    t._refresh_model(ev, now)
    t._refresh_model(ev, now + pd.Timedelta(minutes=1))                 # still running: must not launch a second job
    assert feed.calls == 1 and t.forecast_state == "in_flight"
    feed.release.set()
    _join(t)
    delays = []
    clock = now + pd.Timedelta(minutes=2)
    for _ in range(4):
        t._refresh_model(ev, clock)                                     # collects the failure
        assert t._fail_count >= 1 and t.forecast_state == "idle"
        delays.append((t._next_retry_at - clock) / pd.Timedelta(minutes=1))
        calls = feed.calls
        t._refresh_model(ev, clock + pd.Timedelta(minutes=1))           # inside the backoff window: no hammering
        assert feed.calls == calls
        clock = t._next_retry_at + pd.Timedelta(seconds=1)
        t._refresh_model(ev, clock)                                     # window over: exactly one new job
        _join(t)
    assert delays[1] > delays[0] * 1.3 and delays[2] > delays[1] * 1.3 and delays[-1] <= 72


def test_stale_model_blocks_buys_but_not_status_and_slow_ticks(tmp_path):
    t, ev = make_trader(tmp_path)
    now = ev.start + pd.Timedelta(days=5)
    t._apply_forecast(GOOD, ev, now)
    assert t.buy_block_reason(now + pd.Timedelta(minutes=149), 300, 300) is None
    assert "stale" in t.buy_block_reason(now + pd.Timedelta(minutes=151), 300, 300)      # e.g. after 1051 s slow ticks piling up
    assert "tweet data is stale" in t.buy_block_reason(now, 340, 300)
    t.tick(now + pd.Timedelta(minutes=200))          # stale forecast + FakeFeed refresh succeeds in replay mode -> refreshed
    # now make refresh fail: a tick with a stale model records "blocked" and does not buy
    class Failing(FakeFeed):
        def forecast(self, *a, **k):
            return None
    t.feed = Failing()
    n = t.account.state["n_buys"]
    t.tick(now + pd.Timedelta(minutes=400))
    assert t.account.state["n_buys"] == n
    rows = list(csv.DictReader(open(tmp_path / "decisions.csv")))
    assert "blocked" in rows[-1]["result"]


def test_forecast_for_old_event_is_discarded_after_roll(tmp_path):
    feed = CountingFeed(ok=True)
    feed.release.set()
    t = PaperTrader(feed, Rules(), str(tmp_path), 30.0, b=1.0, chart_every=1000)
    ev = make_event()
    now = ev.start + pd.Timedelta(days=5)
    t._refresh_model(ev, now)                       # launched for "fake"
    _join(t)
    other = make_event()
    other.slug = "next-week"
    t._refresh_model(other, now + pd.Timedelta(minutes=1))     # result arrives while trading another event
    assert not t.model.ready


# ================================================================ B03 durable state
from src.simulation.paper_trader.account import PaperAccount
from src.simulation.paper_trader.checkpoint import StateMissingError, load_latest_valid, write_checkpoint
from src.simulation.paper_trader.fills import buy_with_budget, FeeSchedule


def _traded_account(run_dir):
    a = PaperAccount(str(run_dir), 30.0)
    f = buy_with_budget([(0.05, 1000)], 1.0, FeeSchedule(0.05, 1.0))
    a.buy("e|b", "e", "b", "tok", f, pd.Timestamp("2026-11-01 12:00", tz="UTC"))
    return a


def test_restore_from_backup_after_run_folder_is_destroyed(tmp_path):
    run, backup = tmp_path / "runs" / "live", tmp_path / "backup"
    a = _traded_account(run)
    write_checkpoint(str(run), str(backup))
    ledger = (run / "trades.csv").read_text()
    import shutil
    shutil.rmtree(run)                                      # the shared-computer reset
    b = PaperAccount(str(run), 999, backup_dir=str(backup))
    assert b.state == a.state and b.state["last_buy_ts"] and list(b.positions) == ["e|b"]
    assert (run / "trades.csv").read_text() == ledger


def test_corrupt_newest_checkpoint_falls_back_to_older(tmp_path):
    run = tmp_path / "live"
    a = _traded_account(run)
    p1 = write_checkpoint(str(run))
    cash1 = a.cash
    a.state["cash"] -= 1
    a.save()
    p2 = write_checkpoint(str(run))
    open(p2, "w").write(open(p2).read()[:-30])              # truncate newest
    payload, bad = load_latest_valid(str(run / "checkpoints"))
    assert payload["state"]["cash"] == cash1 and bad == [p2]
    os.remove(run / "state.json")
    assert PaperAccount(str(run), 5).cash == cash1


def test_missing_state_with_prior_run_is_refused_unless_authorised(tmp_path):
    run = tmp_path / "live"
    _traded_account(run)
    os.remove(run / "state.json")                           # state lost, ledger and logs still there, no checkpoint
    with pytest.raises(StateMissingError):
        PaperAccount(str(run), 40)
    fresh = PaperAccount(str(run), 40, allow_new_state=True)
    assert fresh.cash == 40
    PaperAccount(str(tmp_path / "brand-new"), 40)           # a genuinely new folder is fine


def test_checkpoint_contains_no_secrets_and_runner_writes_one_per_tick(tmp_path):
    t, ev = make_trader(tmp_path)
    t.feed.mode = "live"
    t.feed.local_count = lambda e, n: (300, None)
    t.feed.next_event = lambda *a: None
    now = ev.start + pd.Timedelta(days=5)
    t._apply_forecast(GOOD, ev, now)
    t.tick(now)
    payload, _ = load_latest_valid(str(tmp_path / "checkpoints"))
    assert set(payload) == {"schema", "run", "seq", "ts_utc", "git_commit", "state", "forecast_state", "trades_csv"}
    assert payload["forecast_state"]["event_slug"] == "fake"


# ================================================================ B13 ensemble attribution
class _DP:
    def get_current_week_data(self, t):
        return {"current_week_tweets": 100, "time_remaining": pd.Timedelta(days=1)}


def _predictor(weights):
    sys.path.insert(0, os.path.join(ROOT, "src"))
    try:
        from prediction_algos.ensemble.predictor import EnsembleTweetPredictor
    except ImportError as ex:                       # light install: the heavy ensemble libraries are not present
        pytest.skip(f"ensemble libraries not installed: {ex}")
    p = EnsembleTweetPredictor.__new__(EnsembleTweetPredictor)
    p.normalized_weights = weights
    p.data_processor = _DP()
    return p


W = {"neural_prophet": 0.4, "facebook_prophet": 0.3, "timesfm": 0.2, "moving_average": 0.1}


def _results(skip=None):
    r = {"neural_prophet": {"prediction_results": {"total_predicted": 100.0}},
         "facebook_prophet": {"total_predicted": 200.0},
         "timesfm": {"ensemble_results": {"total_predicted": 300.0}}}
    if skip:
        r[skip] = {"error": "model blew up"}              # present but unusable
    return r


@pytest.mark.parametrize("skip", [None, "neural_prophet", "facebook_prophet", "timesfm"])
def test_contributions_map_each_name_to_its_own_prediction(skip):
    pred = _predictor(W)
    out = pred._combine_predictions(_results(skip), {"moving_average": {"total_predicted": 400.0}}, None)
    c = out["model_contributions"]
    truth = {"neural_prophet": 100.0, "facebook_prophet": 200.0, "timesfm": 300.0, "moving_average": 400.0}
    expected = {k: v for k, v in truth.items() if k != skip}
    assert {k: v["prediction"] for k, v in c.items()} == expected
    assert sum(v["weight"] for v in c.values()) == pytest.approx(1.0)
    assert c["moving_average"]["type"] == "additional_method"
    assert out["total_predicted"] == pytest.approx(sum(expected[k] * c[k]["weight"] for k in expected))


def test_too_many_failed_models_is_refused():
    pred = _predictor(W)
    bad = {k: {"error": "x"} for k in ("neural_prophet", "facebook_prophet")}
    bad["timesfm"] = {"ensemble_results": {"total_predicted": 300.0}}
    with pytest.raises(ValueError):
        pred._combine_predictions(bad, {}, None)          # only 20% of the weight survived


# ================================================================ B12 quote-less equity
def _held(tmp_path):
    a = PaperAccount(str(tmp_path), 30.0)
    f = buy_with_budget([(0.05, 1000)], 1.0, FeeSchedule(0.05, 1.0))
    a.buy("e|b", "e", "b", "tok", f, pd.Timestamp("2026-11-01 12:00", tz="UTC"))
    return a, f


NOW = pd.Timestamp("2026-11-02 12:00", tz="UTC").to_pydatetime()


def test_equity_never_assumes_cost_recovery(tmp_path):
    a, f = _held(tmp_path)
    cost = a.positions["e|b"]["cost_usd"]
    fees = {"e|b": FeeSchedule(0.05, 1.0)}
    # 1) no quote at all and no prior mark -> 0, flagged (old code returned the cost)
    eq = a.equity({}, fees, NOW)
    assert eq["positions_bid_value"] == 0.0 and eq["unquoted_positions"] == 1 and eq["held_coverage"] == 0.0
    # 2) book with asks but an empty bid side -> nothing is sellable
    eq = a.equity({"e|b": Quote([], [(0.9, 10)])}, fees, NOW)
    assert eq["positions_bid_value"] == 0.0 and eq["equity_conservative"] == pytest.approx(a.cash)
    # 3) quoted -> bid value net of fee, remembered
    eq = a.equity({"e|b": Quote([(0.02, 1000)], [(0.03, 1000)])}, fees, NOW)
    assert eq["positions_bid_value"] == pytest.approx(f.shares * 0.02 - taker_fee_(f.shares, 0.02)) and eq["unquoted_positions"] == 0
    assert eq["positions_bid_value"] < cost
    # 4) transient failure shortly after: last mark, flagged stale; long after: 0
    soon = a.equity({}, fees, NOW + pd.Timedelta(minutes=10))
    assert soon["stale_mark_value"] == pytest.approx(eq["positions_bid_value"]) and soon["unquoted_positions"] == 1
    late = a.equity({}, fees, NOW + pd.Timedelta(hours=3))
    assert late["positions_bid_value"] == 0.0
    # 5) partial coverage
    a2 = PaperAccount(str(tmp_path / "two"), 30.0)
    for k in ("x", "y"):
        a2.buy(f"e|{k}", "e", k, "t", f, pd.Timestamp("2026-11-01", tz="UTC"))
    eq = a2.equity({"e|x": Quote([(0.05, 100)], [(0.06, 100)])}, {}, NOW)
    assert eq["held_coverage"] == 0.5


def taker_fee_(shares, price):
    from src.simulation.paper_trader.fills import taker_fee
    return taker_fee(shares, price, FeeSchedule(0.05, 1.0))


# ================================================================ B09 net edge / B10 exposure / B11 exits
from src.simulation.paper_trader.strategy import buy_candidates, plan_sell, risk_filter, sell_reason
from src.simulation.paper_trader.fills import sell_shares

HIGH_FEE = FeeSchedule(0.25, 1.0)


def test_fees_can_reverse_a_gross_edge():
    quotes = {"a": Quote([(0.08, 1000)], [(0.09, 1000)])}
    preds = {"a": 0.1025}                                              # gross 1.25pt > the 1pt rule
    assert [c["bucket"] for c in buy_candidates(preds, quotes, Rules())] == ["a"]               # no-fee compatibility
    assert [c["bucket"] for c in buy_candidates(preds, quotes, Rules(), {"a": FeeSchedule(0.05, 1)})] == ["a"]
    assert buy_candidates(preds, quotes, Rules(), {"a": HIGH_FEE}) == []                        # fees reverse it
    c = buy_candidates(preds, quotes, Rules(), {"a": FeeSchedule(0.05, 1)})[0]
    assert c["net_edge"] == pytest.approx(c["edge"] - c["est_costs"]) and c["est_costs"] == pytest.approx(2 * 0.05 * 0.09 * 0.91)
    assert buy_candidates(preds, quotes, Rules(min_net_edge=0.01), {"a": FeeSchedule(0.05, 1)}) == []   # margin knob
    assert buy_candidates(preds, quotes, Rules(include_exit_fee=False), {"a": FeeSchedule(0.05, 1)})[0]["est_costs"] == pytest.approx(0.05 * 0.09 * 0.91)
    cheap = {"a": Quote([(0.04, 1000)], [(0.05, 1000)])}                                       # ~5c contract
    assert buy_candidates({"a": 0.0625}, cheap, Rules(), {"a": FeeSchedule(0.05, 1)}) == []     # pred < 8% anyway
    assert len(buy_candidates({"a": 0.10}, cheap, Rules(), {"a": FeeSchedule(0.05, 1)})) == 1


def test_buy_rejected_when_the_executable_fill_has_no_net_edge(tmp_path):
    t, ev = make_trader(tmp_path)
    now = ev.start + pd.Timedelta(days=5)
    t._apply_forecast(GOOD, ev, now)
    preds = dict(zip([b.title for b in ev.buckets], t.model.probs(ev.ranges, 300, ev.days_left(now)).tolist()))
    bucket = max(preds, key=preds.get)
    ask = max(0.0, preds[bucket] - 0.05)
    t.feed.books = {bucket: Quote([(ask - 0.01, 500)], [(round(ask, 4), 1.0), (round(ask + 0.0095, 4), 500)])}   # 1 share at the touch, rest deeper
    fees = {b.title: b.fees for b in ev.buckets}
    top_net = buy_candidates({bucket: preds[bucket]}, t.feed.books, Rules(), fees)[0]["net_edge"]
    t.rules = Rules(min_net_edge=top_net - 0.004, min_shares=0.0)          # top of book passes, the real (deeper) fill cannot
    t.tick(now)
    assert t.account.state["n_buys"] == 0
    assert "rejected: net edge" in list(csv.DictReader(open(tmp_path / "decisions.csv")))[-1]["result"]


def test_decision_log_records_gross_costs_and_net(tmp_path):
    t, ev = make_trader(tmp_path)
    now = ev.start + pd.Timedelta(days=5)
    t._apply_forecast(GOOD, ev, now)
    t.tick(now)
    r = list(csv.DictReader(open(tmp_path / "decisions.csv")))[-1]
    assert "BOUGHT" in r["result"] and float(r["net_edge"]) == pytest.approx(float(r["gross_edge"]) - float(r["est_costs"]), abs=1e-4)


ORDER = ["a", "b", "c", "d", "e"]
PREDS = {"a": 0.05, "b": 0.20, "c": 0.35, "d": 0.25, "e": 0.15}


def cand(t):
    return {"bucket": t, "pred": PREDS[t], "ask": 0.1, "edge": PREDS[t] - 0.1}


def test_risk_limits():
    r = Rules(stake=1.0, max_bucket_frac=0.2, max_tail_frac=0.3, max_event_frac=0.5, min_cash_reserve=0.0)
    # bucket cap: 20% of 10 = 2.0 -> a second $1 add fits, a third does not
    assert risk_filter([cand("d")], {"d": 1.0}, ORDER, PREDS, 10, 10, 9, r)[0]
    assert not risk_filter([cand("d")], {"d": 2.0}, ORDER, PREDS, 10, 10, 8, r)[0]
    # tail cap: d and e are both above the modal bucket c; 30% of 10 = 3.0
    held = {"d": 1.5, "e": 1.5}
    el, rej = risk_filter([cand("e")], held, ORDER, PREDS, 10, 10, 7, Rules(max_bucket_frac=0.9, max_tail_frac=0.3, max_event_frac=0.9))
    assert not el and "tail cap" in rej[0][1]
    assert risk_filter([cand("b")], held, ORDER, PREDS, 10, 10, 7, Rules(max_bucket_frac=0.9, max_tail_frac=0.3, max_event_frac=0.9))[0]   # other side is free
    # event cap, cash reserve, drawdown stop
    assert not risk_filter([cand("b")], {"a": 2.5, "c": 2.0}, ORDER, PREDS, 10, 10, 5.5, Rules(max_bucket_frac=0.9, max_tail_frac=0.9, max_event_frac=0.5))[0]
    assert not risk_filter([cand("b")], {}, ORDER, PREDS, 10, 10, 1.5, Rules(min_cash_reserve=1.0))[0]
    assert not risk_filter([cand("b")], {}, ORDER, PREDS, 4, 10, 4, Rules(drawdown_stop=0.5))[0]
    assert risk_filter([cand("b")], {}, ORDER, PREDS, 6, 10, 6, Rules(drawdown_stop=0.5))[0]
    # a bigger edge does not override a limit
    big = dict(cand("d"), ask=0.01, edge=0.24)
    assert not risk_filter([big], {"d": 2.0}, ORDER, PREDS, 10, 10, 8, r)[0]


def test_repeated_averaging_down_is_capped_in_the_engine(tmp_path):
    ev = make_event()
    feed = FakeFeed()
    feed.books = {"400-419": Quote([(0.13, 500)], [(0.15, 500)])}       # one attractive bucket, offered every single tick
    t = PaperTrader(feed, Rules(), str(tmp_path), 12.0, buy_every_min=1, sell_every_min=1, b=1.0, start_after_days=0, chart_every=1000)
    t.event, t.events["fake"] = ev, ev
    now = ev.start + pd.Timedelta(days=5)
    for i in range(30):                                                  # the old code kept buying until cash ran out (~11 buys)
        t.tick(now + pd.Timedelta(minutes=2 * i))
    cost = sum(p["cost_usd"] for p in t.account.positions.values())
    assert 1 <= t.account.state["n_buys"] <= 3 and cost <= 0.25 * 12.0 + 1e-6
    assert "risk limits" in list(csv.DictReader(open(tmp_path / "decisions.csv")))[-1]["result"]


def test_exit_never_walks_into_disastrous_depth():
    r = Rules()
    book = [(0.50, 10), (0.01, 1000)]
    naive = sell_shares(book, 100, FeeSchedule(0.05, 1))
    assert naive.shares == 100 and naive.avg_price < 0.1                 # what the old code did: dump at any price
    fill, why = plan_sell(book, 100, FeeSchedule(0.05, 1), 0.02, "pred 2.0% < 4%", r)
    assert fill.shares == 10 and fill.avg_price == 0.5                   # partial, only the acceptable level
    assert plan_sell([], 10, FeeSchedule(), 0.02, "x", r)[0] is None
    fill, why = plan_sell([(0.004, 5)], 10, FeeSchedule(0.05, 1), 0.039, "pred 3.9% < 4%", Rules(exit_min_ratio=0.5))
    assert fill is None and "below" in why                               # 0.4c vs 3.9c model value: hold
    assert plan_sell([(0.004, 5)], 10, FeeSchedule(0.05, 1), 0.039, "pred 3.9% < 4%", Rules())[0] is not None   # default unchanged


def test_sell_hysteresis_prevents_borderline_flip():
    assert sell_reason(0.10, 0.101, Rules(sell_hysteresis=0.01)) is None
    assert sell_reason(0.10, 0.12, Rules(sell_hysteresis=0.01))
    assert sell_reason(0.10, 0.101, Rules())                             # default behaviour unchanged


def test_partial_exit_keeps_accounting_consistent(tmp_path):
    ev = make_event()
    feed = FakeFeed()
    t = PaperTrader(feed, Rules(), str(tmp_path), 30.0, buy_every_min=60, sell_every_min=10, b=1.0, start_after_days=0, chart_every=1000)
    t.event, t.events["fake"] = ev, ev
    f = buy_with_budget([(0.10, 1000)], 3.0, FeeSchedule(0.05, 1.0))
    t.account.buy("fake|400-419", "fake", "400-419", "tok", f, pd.Timestamp("2026-10-30", tz="UTC"))
    shares0, cost0, cash0 = f.shares, t.account.positions["fake|400-419"]["cost_usd"], t.account.cash
    feed.books = {"400-419": Quote([(0.95, 5), (0.01, 1000)], [(0.97, 500)])}
    now = ev.start + pd.Timedelta(days=5)
    t._apply_forecast(GOOD, ev, now)
    t.tick(now)
    pos = t.account.positions["fake|400-419"]
    assert pos["shares"] == pytest.approx(shares0 - 5) and pos["cost_usd"] == pytest.approx(cost0 * (shares0 - 5) / shares0)
    sold = t.account.cash - cash0
    assert sold == pytest.approx(5 * 0.95 - taker_fee_(5, 0.95), abs=1e-4)


# ================================================================ B14 writer serialisation / B17 docs+CI
def test_file_lock_serialises_writers(tmp_path):
    from src.simulation.paper_trader.procutil import file_lock
    path = str(tmp_path / ".lock")
    code = ("import sys,time;sys.path.insert(0,%r);from src.simulation.paper_trader.procutil import file_lock;"
            "l=file_lock(%r);l.__enter__();print('in',flush=True);time.sleep(30)" % (ROOT, path))
    child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True, cwd=ROOT)
    try:
        assert child.stdout.readline().strip() == "in"
        with pytest.raises(TimeoutError):
            with file_lock(path, timeout=0.6, poll=0.1):
                pass
        child.kill()
        child.wait()
        with file_lock(path, timeout=2):                    # dead writer's lock is released by the kernel
            pass
    finally:
        child.kill()


def test_atomic_state_writes_use_unique_temp_files(tmp_path):
    a = PaperAccount(str(tmp_path), 30.0)
    a.save()
    assert not any(n.endswith(".tmp") for n in os.listdir(tmp_path))
    assert json.load(open(tmp_path / "state.json"))["cash"] == 30.0


def test_worker_stderr_kept_for_failed_attempt(monkeypatch, tmp_path):
    from src.simulation.paper_trader import feeds
    ok_refresh = subprocess.CompletedProcess([], 0, 'REFRESH_RESULT {"new_rows": 0, "total_rows": 1, "newest": "x", "sha256": "h"}', "")
    bad_worker = subprocess.CompletedProcess([], 3, "", "Traceback ... CmdStan interrupted")
    seq = iter([ok_refresh, bad_worker])
    monkeypatch.setattr(feeds.subprocess, "run", lambda *a, **k: next(seq))
    f = feeds.LiveFeed()
    monkeypatch.setattr(f, "csv_path", str(tmp_path / "data.csv"))
    (tmp_path / "data.csv").write_text("id,text,created_at\n")
    assert f.forecast(make_event(), pd.Timestamp("2026-11-03 12:00", tz="UTC"), str(tmp_path)) is None
    errs = [n for n in os.listdir(tmp_path / "model_logs") if n.endswith(".stderr")]
    assert len(errs) == 1 and "CmdStan interrupted" in open(tmp_path / "model_logs" / errs[0]).read()
    assert not [n for n in os.listdir(tmp_path / "model_logs") if n.startswith("data_")]     # snapshot cleaned up


def test_runbook_and_ci_are_linux_ready():
    rb = open(os.path.join(ROOT, "src/simulation/paper_trader/RUNBOOK.md")).read()
    assert "15 passed" not in rb and "Linux" in rb
    assert os.path.exists(os.path.join(ROOT, ".github/workflows/tests.yml"))
    assert "Restart=on-failure" in open(os.path.join(ROOT, "src/simulation/paper_trader/deploy/paper-trader.service")).read()


# ================================================================ light model + backtested strategy preset
from src.simulation.paper_trader.light_model import LightModel, LightParams, LightPredictor, load_times
from src.simulation.paper_trader.strategy import choose_buy

REAL_CSV = os.path.join(ROOT, "src", "data", "elonmusk_reformatted.csv")


@pytest.fixture(scope="module")
def times():
    return load_times(REAL_CSV)


RANGES20 = [(i, i + 19) for i in range(0, 700, 20)]
S0, E0 = pd.Timestamp("2026-10-20 12:00"), pd.Timestamp("2026-10-27 12:00")        # naive ET


def _count(times, a, b):
    return int(np.searchsorted(times, np.datetime64(b), "right") - np.searchsorted(times, np.datetime64(a), "left"))


def test_light_probs_are_a_distribution_and_move_with_the_count(times):
    now = S0 + pd.Timedelta(days=3)
    m = LightModel(times).fit(now)
    so = _count(times, S0, now)
    p = m.bucket_probs(RANGES20, S0, now, E0, so)
    assert p.sum() == pytest.approx(1.0) and (p >= 0).all()
    mean = lambda q: sum(q[i] * (RANGES20[i][0] + 10) for i in range(len(q)))
    assert mean(m.bucket_probs(RANGES20, S0, now, E0, so + 60)) > mean(p) + 40       # more tweets so far -> higher final
    assert (p[: so // 20] == 0).all()                                                  # buckets already passed are impossible
    with pytest.raises(ForecastError):
        m.bucket_probs(RANGES20, S0, now, E0, -3)


def test_light_model_is_causal(times):
    now = S0 + pd.Timedelta(days=3)
    so = _count(times, S0, now)
    full = LightModel(times).fit(now).bucket_probs(RANGES20, S0, now, E0, so)
    cut = times[times <= np.datetime64(now)]
    only_past = LightModel(cut).fit(now).bucket_probs(RANGES20, S0, now, E0, so)
    assert np.allclose(full, only_past)                                               # tweets after `now` change nothing


def test_stale_history_is_not_read_as_a_quiet_week(times):
    now = S0 + pd.Timedelta(days=3)
    stale = times[times <= np.datetime64(now - pd.Timedelta(days=2))]               # CSV stopped 2 days ago
    m = LightModel(stale).fit(now)
    fresh = LightModel(times).fit(now)
    assert m.level > 0.6 * fresh.level                                              # old code-style zero-fill would give ~ 1/3 of it


def test_light_predictor_adapter_and_speed(times):
    import time as _t
    lp = LightPredictor(REAL_CSV)
    assert lp.ready
    ev = make_event()
    ev.start, ev.end = pd.Timestamp("2026-10-27 16:00", tz="UTC"), pd.Timestamp("2026-11-03 17:00", tz="UTC")
    now = pd.Timestamp("2026-10-30 16:00", tz="UTC")
    t0 = _t.time()
    p = lp.probs([(i, i + 19) for i in range(0, 700, 20)], 120, None, event=ev, now=now)
    assert _t.time() - t0 < 1.0 and p.sum() == pytest.approx(1.0) and lp.last_mean_total > 120
    lagged = LightPredictor(REAL_CSV, count_lag_h=3)
    lagged.probs([(i, i + 19) for i in range(0, 700, 20)], 120, None, event=ev, now=now)
    assert lagged.last_mean_total > lp.last_mean_total                              # unseen tweets are added back


def test_top_k_and_best_pick_and_no_averaging_down():
    quotes = {t: Quote([(0.01, 100)], [(0.05, 100)]) for t in "abcd"}
    preds = {"a": 0.40, "b": 0.30, "c": 0.20, "d": 0.10}
    r = Rules(top_k=2)
    assert [c["bucket"] for c in buy_candidates(preds, quotes, r)] == ["a", "b"]
    assert len(buy_candidates(preds, quotes, Rules(top_k=0))) == 4
    cands = buy_candidates(preds, quotes, r)
    assert choose_buy(cands, np.random.default_rng(0), best=True)["bucket"] == "a"
    rules = Rules(max_adds=0)
    el, rej = risk_filter([cand("c")], {"c": 1.0}, ORDER, PREDS, 10, 10, 9, rules, {"c": 1})
    assert not el and "averaging down" in rej[0][1]
    assert risk_filter([cand("c")], {}, ORDER, PREDS, 10, 10, 10, rules, {})[0]
    assert risk_filter([cand("c")], {"c": 1.0}, ORDER, PREDS, 10, 10, 9, Rules(max_adds=1), {"c": 1})[0]
    assert not risk_filter([cand("c")], {"c": 2.0}, ORDER, PREDS, 10, 10, 8, Rules(max_adds=1), {"c": 2})[0]


def test_presets():
    from src.simulation.paper_trader.__main__ import apply_preset, build_parser
    a = apply_preset(build_parser().parse_args([]))
    assert (a.pred_source, a.top_k, a.max_adds, a.start_after_days, a.no_bid_sell, a.pick_best) == ("light", 2, 0, 4.0, True, True)
    b = apply_preset(build_parser().parse_args(["--strategy", "legacy"]))
    assert (b.pred_source, b.top_k, b.max_adds, b.start_after_days, b.no_bid_sell) == ("calibrated", 0, -1, 2.0, False)
    c = apply_preset(build_parser().parse_args(["--strategy", "legacy", "--max-adds", "0", "--top-k", "3"]))
    assert c.max_adds == 0 and c.top_k == 3                                           # explicit flags beat the preset, even 0


class LightFeed(FakeFeed):
    """Replays Oct 27 - Nov 3 from the real tweet CSV; books are priced so that every bucket looks cheap vs the model."""
    mode = "replay"
    csv_path = REAL_CSV

    def __init__(self):
        self.t = load_times(REAL_CSV)
        self.mult = 0.5
        self.p = None

    def tweet_count(self, event, now):
        f = lambda x: np.datetime64(x.tz_convert("US/Eastern").tz_localize(None))
        return int(np.searchsorted(self.t, f(now), "right") - np.searchsorted(self.t, f(event.start), "left"))

    def quotes(self, event, now):
        lp = LightPredictor(REAL_CSV)
        p = lp.probs(event.ranges, self.tweet_count(event, now), None, event=event, now=now)
        return {b.title: Quote([(max(0.01, x * self.mult - 0.01), 1000)], [(max(0.02, x * self.mult), 1000)]) for b, x in zip(event.buckets, p)}

    def resolution(self, event):
        return None


def light_event():
    start = pd.Timestamp("2026-10-27 16:00", tz="UTC")
    bks = [Bucket(f"{lo}-{lo + 19}", lo, lo + 19, f"t{lo}", FEES_T(0.05, 1.0)) for lo in range(0, 700, 20)]
    return Event("light-fake", "Light fake", start, start + pd.Timedelta(days=7, hours=1), bks)


def test_runner_in_light_mode_buys_top2_never_averages_down_and_never_sells(tmp_path):
    ev, feed = light_event(), LightFeed()
    rules = Rules(min_pred=0.10, min_mkt=0.02, min_edge=0.0, min_net_edge=0.02, include_exit_fee=False, sell_below=0.0,
                  sell_if_bid_above_pred=False, top_k=2, max_adds=0, pick_best=True)
    t = PaperTrader(feed, rules, str(tmp_path), 40.0, "light", buy_every_min=60, sell_every_min=60, start_after_days=4.0, chart_every=10 ** 6)
    t.event, t.events["light-fake"] = ev, ev
    for h in range(96, 7 * 24, 1):
        t.tick(ev.start + pd.Timedelta(hours=h))
    trades = list(csv.DictReader(open(tmp_path / "trades.csv")))
    buys = [x for x in trades if x["action"] == "BUY"]
    assert buys and not [x for x in trades if x["action"] == "SELL"]
    assert len({x["bucket"] for x in buys}) == len(buys)                                # one buy per bucket: no averaging down
    for x in buys:                                                                      # every buy was a top-2 model bucket at decision time
        assert float(x["pred"]) >= 0.10
    assert t.account.cash >= 0 and not os.path.exists(tmp_path / "forecast_state.json")   # no forecast job / restore machinery needed
    assert os.path.getsize(tmp_path / "forecasts.csv") > 0


def test_light_mode_blocks_buys_on_stale_history(tmp_path):
    ev, feed = light_event(), LightFeed()
    t = PaperTrader(feed, Rules(), str(tmp_path), 40.0, "light", chart_every=10 ** 6, max_data_age_h=36.0)
    newest = t.model.newest_tweet().tz_localize("US/Eastern", ambiguous=True)
    assert t.buy_block_reason(newest + pd.Timedelta(hours=10), 100, 100) is None
    assert "stale" in t.buy_block_reason(newest + pd.Timedelta(hours=40), 100, 100)


def test_bid_sell_margin_opt_in():
    from src.simulation.paper_trader.__main__ import apply_preset, build_parser
    a = apply_preset(build_parser().parse_args(["--bid-sell-margin", "5"]))
    assert a.no_bid_sell is False and a.sell_hysteresis == 5.0
    assert apply_preset(build_parser().parse_args([])).no_bid_sell is True            # default light preset still holds
    r = Rules(sell_if_bid_above_pred=True, sell_hysteresis=0.05, sell_below=0.0)
    assert sell_reason(0.60, 0.80, r)                                                  # market pays 80% for what we value at 60%
    assert sell_reason(0.60, 0.63, r) is None


# ================================================================ order sizing (kelly option, 5-share minimum)
from src.simulation.paper_trader.strategy import size_stake

F05 = FeeSchedule(0.05, 1.0)


def test_min_five_shares_raises_the_order_above_one_dollar():
    r = Rules()                                                   # fixed $1 stake
    assert size_stake(r, 0.30, 0.10, F05, 40) == 1.0              # 1 dollar buys ~9.9 shares: fine
    s = size_stake(r, 0.45, 0.30, F05, 40)                        # at 30c, $1 buys only 3 shares -> must be 5 shares' cost
    assert s == pytest.approx(5 * (0.30 + 0.05 * 0.3 * 0.7), abs=0.011) and s > 1.0
    assert buy_with_budget([(0.30, 1000)], s, F05).shares >= 5.0


def test_kelly_sizing_scales_with_edge_and_equity_and_is_bounded():
    r = Rules(kelly=0.25, max_stake=3.0)
    small = size_stake(r, 0.15, 0.12, F05, 40)                    # tiny edge -> the $1 minimum
    big = size_stake(r, 0.45, 0.20, F05, 40)                      # big edge -> more, but never above max_stake
    assert small == 1.0 and 1.0 < big <= 3.0
    assert size_stake(r, 0.45, 0.20, F05, 400) == 3.0             # a bigger account hits the cap
    assert size_stake(r, 0.45, 0.20, F05, 10) < big               # a shrunken account bets less (winnings are reinvested, losses shrink it)
    assert size_stake(Rules(kelly=0.0), 0.45, 0.10, F05, 400) == 1.0   # off by default


def test_engine_never_places_an_order_below_5_shares_or_1_dollar(tmp_path):
    ev, feed = light_event(), LightFeed()
    rules = Rules(min_pred=0.10, min_mkt=0.02, min_edge=0.0, min_net_edge=0.02, include_exit_fee=False, sell_below=0.0,
                  sell_if_bid_above_pred=False, top_k=2, max_adds=0, pick_best=True, kelly=0.25, max_stake=3.0)
    feed.mult = 0.5
    t = PaperTrader(feed, rules, str(tmp_path), 40.0, "light", buy_every_min=60, sell_every_min=60, start_after_days=4.0, chart_every=10 ** 6)
    t.event, t.events["light-fake"] = ev, ev
    for h in range(96, 7 * 24):
        t.tick(ev.start + pd.Timedelta(hours=h))
    buys = [x for x in csv.DictReader(open(tmp_path / "trades.csv")) if x["action"] == "BUY"]
    assert buys
    for x in buys:
        assert float(x["shares"]) >= 5.0 - 1e-9 and float(x["notional"]) + float(x["fee"]) >= 0.99
        assert float(x["notional"]) + float(x["fee"]) <= 3.0 + 0.5


def test_fresh_preset_matches_the_backtested_configuration():
    from src.simulation.paper_trader.__main__ import apply_preset, build_parser
    a = apply_preset(build_parser().parse_args(["--strategy", "fresh"]))
    assert (a.pred_source, a.top_k, a.max_adds, a.start_after_days, a.kelly, a.max_stake) == ("light", 3, 0, 4.0, 0.25, 5.0)
    assert a.no_bid_sell is False and a.sell_hysteresis == 5.0 and a.pick_best is True
    z = apply_preset(build_parser().parse_args(["--strategy", "fresh", "--kelly", "0"]))
    assert z.kelly == 0.0                                                             # explicit zero beats the preset


# ================================================================ machine suspend (61-minute gap seen in live use) / 404 retries
def test_tick_resumes_immediately_after_a_suspend(tmp_path):
    t, _ = make_trader(tmp_path)
    c = Clock()
    wall = {"now": 1_000_000.0}
    t._mono, t._wall = c.mono, lambda: wall["now"]

    def sleep_and_suspend(s):
        c.sleep(s)                                  # monotonic advances only by what we slept ...
        wall["now"] += 3000.0                       # ... but the machine was suspended: the wall clock jumped 50 minutes
    t._sleep = sleep_and_suspend
    t._sleep_until(c.now + 600, wall["now"] + 600)  # a normal 10 minute wait
    assert len(c.sleeps) == 1 and c.sleeps[0] <= 5.0   # returned after the first slice, did NOT wait 600 monotonic seconds more


def test_wall_clock_going_backwards_still_ends_the_sleep_via_the_monotonic_deadline(tmp_path):
    t, _ = make_trader(tmp_path)
    c = Clock()
    t._mono, t._sleep, t._wall = c.mono, c.sleep, lambda: -1e12
    t._sleep_until(c.now + 12, 5e12)                # wall deadline unreachable, monotonic one decides
    assert sum(c.sleeps) == pytest.approx(12.0) and all(x >= 0 for x in c.sleeps)


def test_404_is_not_retried(monkeypatch):
    from src.simulation.paper_trader import feeds
    calls = []

    class R:
        status_code = 404

        def json(self):
            return {}
    monkeypatch.setattr(feeds.requests, "get", lambda *a, **k: calls.append(1) or R())
    monkeypatch.setattr(feeds.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError):
        feeds.http_get("http://x/book")
    assert len(calls) == 1                           # old code: 4 tries with growing sleeps for a book that will never exist
    R.status_code = 503
    calls.clear()
    with pytest.raises(RuntimeError):
        feeds.http_get("http://x/book")
    assert len(calls) == 4                           # transient errors are still retried


def test_light_strategy_does_not_trade_on_a_fallback_tweet_count(tmp_path):
    class LiveLight(LightFeed):
        mode = "live"
        broken = True

        def tweet_count(self, event, now):
            return None if self.broken else LightFeed.tweet_count(self, event, now)

        def quotes(self, event, now):                              # price the books from the TRUE count, whatever tweet_count() returns
            lp = LightPredictor(REAL_CSV)
            p = lp.probs(event.ranges, LightFeed.tweet_count(self, event, now), None, event=event, now=now)
            return {b.title: Quote([(max(0.01, x * self.mult - 0.01), 1000)], [(max(0.02, x * self.mult), 1000)]) for b, x in zip(event.buckets, p)}

        def local_count(self, event, now):
            return LightFeed.tweet_count(self, event, now), None

        def next_event(self, *a):
            return None
    ev, feed = light_event(), LiveLight()
    rules = Rules(min_pred=0.10, min_mkt=0.02, min_edge=0.0, min_net_edge=0.02, include_exit_fee=False, top_k=3, max_adds=0, pick_best=True,
                  sell_if_bid_above_pred=True, sell_hysteresis=0.05)
    t = PaperTrader(feed, rules, str(tmp_path), 40.0, "light", buy_every_min=60, sell_every_min=60, start_after_days=4.0, chart_every=10 ** 6)
    t.event, t.events["light-fake"] = ev, ev
    now = ev.start + pd.Timedelta(days=5)
    t._refresh_light = lambda *a, **k: None                           # no background XTracker refresh in this test
    t.tick(now)
    assert t._count_source == "local_csv"
    assert "unavailable from Polymarket" in t.buy_block_reason(now, None, 100)
    assert t.account.state["n_buys"] == 0
    assert "blocked" in list(csv.DictReader(open(tmp_path / "decisions.csv")))[-1]["result"]
    feed.broken = False                                           # Polymarket's count is back -> trading is allowed again
    t.tick(now + pd.Timedelta(hours=1))
    assert t._count_source == "polymarket" and t.buy_block_reason(now, 100, 100) is None


def test_light_start_refreshes_tweet_history_before_the_first_decision(tmp_path):
    order = []

    class RefreshFeed(LightFeed):
        mode = "live"

        def refresh_tweet_data(self):
            order.append("refresh")
            return {"ok": True, "new_tweets": 3}

        def quotes(self, event, now):
            order.append("quotes")
            return LightFeed.quotes(self, event, now)

        def local_count(self, event, now):
            return LightFeed.tweet_count(self, event, now), None

        def next_event(self, *a):
            return None
    ev, feed = light_event(), RefreshFeed()
    t = PaperTrader(feed, Rules(top_k=3), str(tmp_path), 40.0, "light", start_after_days=4.0, chart_every=10 ** 6)
    t.event, t.events["light-fake"] = ev, ev
    t.tick(ev.start + pd.Timedelta(days=5))
    assert order.count("refresh") == 1
    # the refresh happened synchronously inside the first tick (not in a background thread that finishes later)
    assert t.forecast_state == "idle" and t._last_forecast_at is not None
    n = order.count("refresh")
    t.tick(ev.start + pd.Timedelta(days=5, minutes=10))                 # later ticks do NOT refresh again (3 h interval)
    assert order.count("refresh") == n
