"""
Durable, verifiable checkpoints of a run (B03).

Every checkpoint is one JSON envelope {"sha256", "payload"}: payload = run name, monotonic sequence, UTC time, git
commit, the full account state, the applied forecast and the complete trade ledger. The checksum covers the canonical
payload, so a truncated/corrupted newest file is detected and the previous checkpoint is used instead.

Where they go: <run dir>/checkpoints/ always, plus <backup_dir>/<run name>/ when a backup dir is given (point that at
another disk / synced folder - the audited incident lost the whole checkout). No secrets are ever included: only
state.json, forecast_state.json and trades.csv are read.
"""
import contextlib
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from .procutil import atomic_write_text, utc_iso

log = logging.getLogger("paper_trader.checkpoint")
SCHEMA = 1
ROOT = Path(__file__).resolve().parents[3]
_NAME = re.compile(r"ckpt_(\d{8})\.json$")


class StateMissingError(RuntimeError):
    """The run folder shows signs of an earlier run but its state is gone and no valid checkpoint exists."""


def _digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _commit() -> str:
    with contextlib.suppress(Exception):
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5).stdout.strip()
    return ""


def _files(directory: str) -> List[Tuple[int, str]]:
    if not os.path.isdir(directory):
        return []
    out = []
    for n in os.listdir(directory):
        m = _NAME.match(n)
        if m:
            out.append((int(m.group(1)), os.path.join(directory, n)))
    return sorted(out)


def _read(run_dir, name):
    p = os.path.join(run_dir, name)
    return open(p).read() if os.path.exists(p) else None


def write_checkpoint(run_dir: str, backup_dir: Optional[str] = None, keep: int = 144) -> str:
    ck_dir = os.path.join(run_dir, "checkpoints")
    os.makedirs(ck_dir, exist_ok=True)
    existing = _files(ck_dir)
    if backup_dir:
        existing += _files(os.path.join(backup_dir, os.path.basename(os.path.abspath(run_dir))))
    seq = max([s for s, _ in existing], default=0) + 1
    state = _read(run_dir, "state.json")
    if state is None:
        raise FileNotFoundError("no state.json to checkpoint")
    payload = {"schema": SCHEMA, "run": os.path.basename(os.path.abspath(run_dir)), "seq": seq, "ts_utc": utc_iso(),
               "git_commit": _commit(), "state": json.loads(state),
               "forecast_state": json.loads(_read(run_dir, "forecast_state.json") or "null"),
               "trades_csv": _read(run_dir, "trades.csv")}
    text = json.dumps({"sha256": _digest(payload), "payload": payload})
    path = os.path.join(ck_dir, f"ckpt_{seq:08d}.json")
    atomic_write_text(path, text)
    for _, old in _files(ck_dir)[:-keep]:
        with contextlib.suppress(OSError):
            os.remove(old)
    if backup_dir:
        try:
            bdir = os.path.join(backup_dir, payload["run"])
            os.makedirs(bdir, exist_ok=True)
            atomic_write_text(os.path.join(bdir, os.path.basename(path)), text)
            for _, old in _files(bdir)[:-keep]:
                with contextlib.suppress(OSError):
                    os.remove(old)
        except Exception as ex:                              # a broken backup disk must not stop trading, but must be loud
            log.error("BACKUP FAILED (%s): %r - checkpoints exist only locally", backup_dir, ex)
    return path


def load_latest_valid(*dirs: str) -> Tuple[Optional[dict], List[str]]:
    """Newest checkpoint whose checksum verifies, searching all dirs; plus the list of corrupt files that were skipped."""
    cands = sorted((c for d in dirs for c in _files(d)), reverse=True)
    bad = []
    for _, path in cands:
        try:
            env = json.load(open(path))
            if env["sha256"] != _digest(env["payload"]) or env["payload"].get("schema") != SCHEMA:
                raise ValueError("checksum mismatch")
            return env["payload"], bad
        except Exception as ex:
            log.error("corrupt checkpoint %s skipped: %r", path, ex)
            bad.append(path)
    return None, bad


def restore_into(run_dir: str, payload: dict):
    """Rewrite state.json (+ forecast_state.json, and trades.csv if it is gone) from a checkpoint payload."""
    os.makedirs(run_dir, exist_ok=True)
    atomic_write_text(os.path.join(run_dir, "state.json"), json.dumps(payload["state"], indent=2))
    if payload.get("forecast_state"):
        atomic_write_text(os.path.join(run_dir, "forecast_state.json"), json.dumps(payload["forecast_state"], indent=2))
    tp = os.path.join(run_dir, "trades.csv")
    if payload.get("trades_csv") and not os.path.exists(tp):
        atomic_write_text(tp, payload["trades_csv"])


def has_prior_run_evidence(run_dir: str) -> bool:
    """Files that only exist if this run folder was used before (config_history.jsonl is excluded: it is written
    before the account is opened on every start)."""
    names = ("trades.csv", "equity.csv", "decisions.csv", "forecast_state.json", "checkpoints")
    return any(os.path.exists(os.path.join(run_dir, n)) for n in names)


def backup_tweet_csv(csv_path: str, backup_dir: str, sha: Optional[str], keep: int = 5):
    """Copy the (mutable) training dataset to the durable destination, named by content hash."""
    d = os.path.join(backup_dir, "tweets")
    os.makedirs(d, exist_ok=True)
    h = (sha or hashlib.sha256(open(csv_path, "rb").read()).hexdigest())[:12]
    dest = os.path.join(d, f"elonmusk_reformatted_{h}.csv")
    if not os.path.exists(dest):
        tmp = dest + ".tmp"
        shutil.copyfile(csv_path, tmp)
        os.replace(tmp, dest)
    olds = sorted((os.path.getmtime(os.path.join(d, n)), n) for n in os.listdir(d) if n.endswith(".csv"))
    for _, n in olds[:-keep]:
        with contextlib.suppress(OSError):
            os.remove(os.path.join(d, n))
