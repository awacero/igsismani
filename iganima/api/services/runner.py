import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime
import os


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")


def write_status(ticket_dir: Path, status: str, message: str):
    status_path = ticket_dir / "status.json"

    data = json.loads(status_path.read_text())
    data["status"] = status
    data["message"] = message
    data["updated_at"] = now_iso()

    status_path.write_text(json.dumps(data, indent=2))


def run_ticket(ticket_dir: Path, event_id: str, iganima_config: str):
    """
    Ejecuta run_igsismani.py como proceso externo.
    """

    logs_dir = ticket_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    stdout_log = logs_dir / "stdout.log"
    stderr_log = logs_dir / "stderr.log"

    write_status(
        ticket_dir,
        status="processing",
        message="Ejecutando generación de video",
    )

    cmd = [
        sys.executable,
        "run_igsismani.py",
        "--iganima_config",
        iganima_config,
        "--event_id",
        event_id,
    ]

    with stdout_log.open("w") as out, stderr_log.open("w") as err:
        process = subprocess.Popen(
            cmd,
            stdout=out,
            stderr=err,
            cwd=os.getcwd(),
        )
        returncode = process.wait()

    if returncode == 0:
        write_status(
            ticket_dir,
            status="done",
            message="Video generado correctamente",
        )
    else:
        write_status(
            ticket_dir,
            status="error",
            message=f"Error durante la ejecución (code {returncode})",
        )
