from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import logging

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_event_id(event_id: str) -> str:
    """
    Normalize event_id to a safe filesystem token.
    Keeps letters, numbers, underscore, dash. Replaces others with underscore.
    """
    event_id = (event_id or "").strip()
    if not event_id:
        raise ValueError("event_id is empty")

    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", event_id).strip("_")
    if not safe:
        raise ValueError("event_id becomes empty after normalization")

    return safe[:64]


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def _new_ticket_id() -> str:
    # 10 chars hex (40 bits): short and easy to handle.
    return secrets.token_hex(5)


def _repo_root() -> Path:
    env = os.environ.get("IGSISMANI_REPO_DIR")
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "run_igsismani.py").exists():
            return p

    here = Path(__file__).resolve().parent
    cur = here
    for _ in range(8):
        if (cur / "run_igsismani.py").exists():
            return cur
        cur = cur.parent

    return Path(os.getcwd()).resolve()


def _event_dir(events_dir: Path, event_id: str) -> Path:
    return (events_dir / event_id).resolve()


def _event_lock_path(events_dir: Path, event_id: str) -> Path:
    return _event_dir(events_dir, event_id) / "event.lock"


def _event_state_path(events_dir: Path, event_id: str) -> Path:
    return _event_dir(events_dir, event_id) / "state.json"


def _ticket_dir(tickets_dir: Path, ticket_id: str) -> Path:
    return (tickets_dir / ticket_id).resolve()


def _ticket_status_path(tickets_dir: Path, ticket_id: str) -> Path:
    return _ticket_dir(tickets_dir, ticket_id) / "status.json"


def _acquire_event_lock(events_dir: Path, event_id: str) -> bool:
    ed = _event_dir(events_dir, event_id)
    ed.mkdir(parents=True, exist_ok=True)
    lock_path = _event_lock_path(events_dir, event_id)

    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(lock_path), flags, 0o644)
    except FileExistsError:
        return False

    try:
        payload = {"event_id": event_id, "created_at": utc_now_iso()}
        os.write(fd, json.dumps(payload).encode("utf-8"))
    finally:
        os.close(fd)
    return True


def _release_event_lock(events_dir: Path, event_id: str) -> None:
    lock_path = _event_lock_path(events_dir, event_id)
    try:
        lock_path.unlink(missing_ok=True)
    except Exception:
        pass


def _init_event_state(event_id: str) -> Dict[str, Any]:
    now = utc_now_iso()
    return {
        "event_id": event_id,
        "status": "idle",
        "active_ticket_id": None,
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "finished_at": None,
        "last_output_file": None,
        "message": None,
    }


def _set_event_state(events_dir: Path, event_id: str, **updates: Any) -> None:
    sp = _event_state_path(events_dir, event_id)
    current = _read_json(sp) if sp.exists() else _init_event_state(event_id)
    current.update(updates)
    current["updated_at"] = utc_now_iso()
    _atomic_write_json(sp, current)


def _init_ticket_status(ticket_id: str, event_id: str) -> Dict[str, Any]:
    now = utc_now_iso()
    return {
        "ticket_id": ticket_id,
        "event_id": event_id,
        "status": "queued",
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "finished_at": None,
        "message": None,
        "output_file": None,
    }


def _set_ticket_status(tickets_dir: Path, ticket_id: str, **updates: Any) -> None:
    sp = _ticket_status_path(tickets_dir, ticket_id)
    current = _read_json(sp) if sp.exists() else {}
    current.update(updates)
    current["updated_at"] = utc_now_iso()
    _atomic_write_json(sp, current)


def _next_output_path(events_dir: Path, event_id: str) -> Path:
    ed = _event_dir(events_dir, event_id)
    ed.mkdir(parents=True, exist_ok=True)
    pat = re.compile(rf"^{re.escape(event_id)}-(\d+)\.mp4$")

    max_n = 0
    for p in ed.iterdir():
        if not p.is_file():
            continue
        m = pat.match(p.name)
        if not m:
            continue
        try:
            n = int(m.group(1))
        except ValueError:
            continue
        max_n = max(max_n, n)

    return ed / f"{event_id}-{max_n + 1}.mp4"


def _find_newest_mp4(root: Path, started_epoch: float) -> Optional[Path]:
    newest: Optional[Path] = None
    newest_mtime = 0.0
    threshold = max(0.0, started_epoch - 2.0)
    for p in root.rglob("*.mp4"):
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if mtime < threshold:
            continue
        if newest is None or mtime > newest_mtime:
            newest = p
            newest_mtime = mtime
    return newest


def get_ticket_status_by_id(
    event_id: str,
    tickets_dir: Path,
    events_dir: Path,
    ticket_id_hint: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if ticket_id_hint:
        sp = _ticket_status_path(tickets_dir, ticket_id_hint)
        if sp.exists():
            try:
                return _read_json(sp)
            except Exception:
                return None
        return None

    stp = _event_state_path(events_dir, event_id)
    if not stp.exists():
        return None
    try:
        state = _read_json(stp)
    except Exception:
        return None

    tid = state.get("active_ticket_id")
    if not tid:
        return None
    sp = _ticket_status_path(tickets_dir, tid)
    if not sp.exists():
        return None
    try:
        return _read_json(sp)
    except Exception:
        return None


def start_video_job(
    *,
    event_id: str,
    artifacts_dir: Path,
    events_dir: Path,
    tickets_dir: Path,
    semaphore: threading.Semaphore,
) -> str:
    event_id = normalize_event_id(event_id)
    events_dir = events_dir.resolve()
    tickets_dir = tickets_dir.resolve()
    artifacts_dir = artifacts_dir.resolve()
    for d in (events_dir, tickets_dir, artifacts_dir):
        d.mkdir(parents=True, exist_ok=True)

    acquired = _acquire_event_lock(events_dir, event_id)
    if not acquired:
        existing = get_ticket_status_by_id(event_id, tickets_dir, events_dir)
        if existing:
            return existing["ticket_id"]
        raise RuntimeError(f"event '{event_id}' is locked but active ticket cannot be determined")

    ticket_id = _new_ticket_id()
    tdir = _ticket_dir(tickets_dir, ticket_id)
    tdir.mkdir(parents=True, exist_ok=True)

    _atomic_write_json(_ticket_status_path(tickets_dir, ticket_id), _init_ticket_status(ticket_id, event_id))
    _set_event_state(events_dir, event_id, status="queued", active_ticket_id=ticket_id, message=None)

    def _worker() -> None:
        print("####start worker")
        logging.info("###Start WORKER ")
        with semaphore:
            started_epoch = time.time()
            _set_ticket_status(tickets_dir, ticket_id, status="processing", started_at=utc_now_iso(), message=None)
            _set_event_state(events_dir, event_id, status="processing", started_at=utc_now_iso(), message=None)

            repo_root = _repo_root()
            script = (repo_root / "run_igsismani.py").resolve()
            stdout_path = tdir / "stdout.log"
            stderr_path = tdir / "stderr.log"

            try:
                if not script.exists():
                    logging.error(f"run_igsismani.py not found under repo root: {repo_root}")
                    raise FileNotFoundError(f"run_igsismani.py not found under repo root: {repo_root}")

                config_env = os.environ.get("IGSISMANI_DEFAULT_IGANIMA_CONFIG")
                if not config_env:
                    raise RuntimeError(
                        "Missing env var IGSISMANI_DEFAULT_IGANIMA_CONFIG "
                        "(path to the iganima config ini for run_igsismani.py)."
                    )
                config_path = Path(config_env).expanduser().resolve()
                if not config_path.exists():
                    logging.error(f"IGSISMANI_DEFAULT_IGANIMA_CONFIG not found: {config_path}")
                    raise FileNotFoundError(f"IGSISMANI_DEFAULT_IGANIMA_CONFIG not found: {config_path}")

                timeout_s = int(os.environ.get("IGSISMANI_JOB_TIMEOUT_SECONDS", "7200"))

                cmd = [
                    "python",
                    str(script),
                    "--iganima_config",
                    str(config_path),
                    "--event_id",
                    str(event_id),
                ]
                logging.info("###Start video creation ")
                with stdout_path.open("w", encoding="utf-8") as out, stderr_path.open("w", encoding="utf-8") as err:
                    proc = subprocess.Popen(
                        cmd,
                        cwd=str(repo_root),
                        stdout=out,
                        stderr=err,
                        env=os.environ.copy(),
                    )
                    try:
                        rc = proc.wait(timeout=timeout_s)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        raise TimeoutError(f"Video job timed out after {timeout_s} seconds")

                if rc != 0:
                    raise RuntimeError(f"Video process exited with code {rc}. See stdout/stderr logs.")

                # Determine next output name while still holding the per-event lock.
                output_path = _next_output_path(events_dir, event_id)

                candidate = _find_newest_mp4(repo_root, started_epoch)
                if candidate is None or not candidate.exists():
                    raise FileNotFoundError(
                        "Video process finished but no MP4 was found. "
                        "Update the pipeline/config to write MP4 outputs, or adjust search strategy."
                    )

                output_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_out = output_path.with_suffix(".mp4.tmp")
                shutil.copy2(candidate, tmp_out)
                tmp_out.replace(output_path)

                rel_output = str(output_path.relative_to(artifacts_dir))

                _set_ticket_status(
                    tickets_dir,
                    ticket_id,
                    status="done",
                    finished_at=utc_now_iso(),
                    message=None,
                    output_file=rel_output,
                )
                _set_event_state(
                    events_dir,
                    event_id,
                    status="done",
                    finished_at=utc_now_iso(),
                    last_output_file=rel_output,
                    message=None,
                )

            except Exception as e:
                _set_ticket_status(
                    tickets_dir,
                    ticket_id,
                    status="error",
                    finished_at=utc_now_iso(),
                    message=str(e),
                )
                _set_event_state(
                    events_dir,
                    event_id,
                    status="error",
                    finished_at=utc_now_iso(),
                    message=str(e),
                )
            finally:
                try:
                    _set_event_state(events_dir, event_id, active_ticket_id=None)
                finally:
                    _release_event_lock(events_dir, event_id)

    threading.Thread(target=_worker, daemon=True).start()
    return ticket_id