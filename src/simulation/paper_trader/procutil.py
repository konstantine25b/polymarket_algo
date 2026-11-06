"""
Process-level safety helpers (no trading logic):

RunLock      a flock held for the whole life of the process. The kernel releases it when the process dies
             (even on SIGKILL), so there is no stale-PID guesswork and two processes can never both own a run.
FileLock     the same thing as a context manager, used to serialise writers of shared files (tweet CSV).
heartbeat    small JSON the supervisor / status can read to see the loop is alive and what it is doing.
exit_status  why the process ended (clean stop, signal, uncaught exception + traceback).
atomic_write_json  write to a unique temp file in the same directory, fsync, os.replace.
"""
import contextlib
import fcntl
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_write_text(path: str, text: str):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=os.path.basename(path) + ".", suffix=".tmp")   # unique per writer
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise


def atomic_write_json(path: str, obj, indent=2):
    atomic_write_text(path, json.dumps(obj, indent=indent))


class AlreadyRunning(RuntimeError):
    pass


class RunLock:
    """Exclusive, process-lifetime lock on <run dir>/run.lock. The file is never unlinked (unlinking a locked
    path is racy); liveness is decided by whether the kernel lock can be taken, never by a PID in the file."""

    def __init__(self, path: str):
        self.path = path
        self._fd = None

    def acquire(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            holder = ""
            with contextlib.suppress(Exception):
                holder = os.read(fd, 400).decode(errors="replace")
            os.close(fd)
            raise AlreadyRunning(f"another paper trader owns {self.path} {holder}")
        os.ftruncate(fd, 0)
        os.write(fd, json.dumps({"pid": os.getpid(), "started_utc": utc_iso(), "argv": sys.argv[1:]}).encode())
        os.fsync(fd)
        self._fd = fd
        return self

    def release(self):
        if self._fd is not None:
            with contextlib.suppress(OSError):
                fcntl.flock(self._fd, fcntl.LOCK_UN)
                os.close(self._fd)
            self._fd = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *exc):
        self.release()


def lock_state(path: str):
    """('absent'|'held'|'free', info dict). 'held' = a live process owns it right now."""
    if not os.path.exists(path):
        return "absent", {}
    info = {}
    with contextlib.suppress(Exception):
        info = json.loads(open(path).read() or "{}")
    fd = os.open(path, os.O_RDONLY)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except OSError:
            return "held", info
        fcntl.flock(fd, fcntl.LOCK_UN)
        return "free", info
    finally:
        os.close(fd)


@contextlib.contextmanager
def file_lock(path: str, timeout: float = 300.0, poll: float = 0.5):
    """Blocking (with timeout) advisory lock for serialising writers of a shared file."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"could not lock {path} within {timeout}s")
                time.sleep(poll)
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def write_heartbeat(run_dir: str, **fields):
    with contextlib.suppress(Exception):
        atomic_write_json(os.path.join(run_dir, "heartbeat.json"), {"ts_utc": utc_iso(), "pid": os.getpid(), **fields})


def write_exit_status(run_dir: str, reason: str, exit_code: int, **fields):
    with contextlib.suppress(Exception):
        atomic_write_json(os.path.join(run_dir, "exit_status.json"),
                          {"ts_utc": utc_iso(), "pid": os.getpid(), "reason": reason, "exit_code": exit_code, **fields})
