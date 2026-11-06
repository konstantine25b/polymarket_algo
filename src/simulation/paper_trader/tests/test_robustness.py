"""Regression tests for the B01-B17 audit (live40, Nov 2-6). Each one reproduces the incident shape."""
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
from src.simulation.paper_trader.strategy import Rules
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
