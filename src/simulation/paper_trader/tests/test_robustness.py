"""Regression tests for the B01-B17 audit (live40, Nov 2-6). Each one reproduces the incident shape."""
import csv
import json
import logging
import os
import subprocess
import sys
import time

import pandas as pd
import pytest

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
    wall = iter([-5e9, 1e12, 7.0, 600.0, 1.23e9])          # backwards / huge jumps
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
