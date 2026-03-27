from __future__ import annotations


from dotenv import load_dotenv
from pathlib import Path

# Carga el archivo .env desde el root del proyecto
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")


import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel
import logging, logging.config


# NOTE:
# Place runner.py in the same package/module path as this file expects.
# If you keep package imports, change this to: from iganima.api.runner import start_video_job
from iganima.api.runner import start_video_job, normalize_event_id, get_ticket_status_by_id, resolve_ticket_video_path


    
print("Start of logging configuration")
logging_ini = os.environ.get("IGSISMANI_LOGGING_INI")
#logging.config.fileConfig(Path("./config/",'logging.ini'), disable_existing_loggers=True)
logging.config.fileConfig(logging_ini)
logger = logging.getLogger(__name__)
logger.info(f"Logger configured was {logging.getLogger().handlers} ")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ARTIFACTS_DIR = Path(os.environ.get("IGSISMANI_ARTIFACTS_DIR", "./artifacts")).resolve()
EVENTS_DIR = (ARTIFACTS_DIR / "events").resolve()
TICKETS_DIR = (ARTIFACTS_DIR / "tickets").resolve()
for d in (ARTIFACTS_DIR, EVENTS_DIR, TICKETS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Global concurrency guard (protects CPU/RAM/GPU).
MAX_CONCURRENT_JOBS = int(os.environ.get("IGSISMANI_MAX_CONCURRENT_JOBS", "1"))
_JOB_SEMAPHORE = threading.Semaphore(MAX_CONCURRENT_JOBS)

logger.info("API starting: artifacts_dir=%s events_dir=%s tickets_dir=%s", ARTIFACTS_DIR, EVENTS_DIR, TICKETS_DIR)
logger.info("API config: max_concurrent_jobs=%s", MAX_CONCURRENT_JOBS)


class CreateTicketResponse(BaseModel):
    ticket_id: str
    status: str
    status_url: str
    deduplicated: bool = False


class TicketStatus(BaseModel):
    ticket_id: str
    event_id: str
    status: str
    created_at: str
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    message: Optional[str] = None
    output_file: Optional[str] = None  # relative path from ARTIFACTS_DIR


app = FastAPI(title="igsismani ticket service (GET)")


@app.get("/ui", response_class=HTMLResponse)
def ui_home():
    return """
    <html>
    <head>
        <title>IGSISMANI Video Service</title>
    </head>
    <body>
        <h2>IGSISMANI Video Service</h2>
        <form action="/ui/create" method="get">
            <label for="event_id">Event ID:</label>
            <input type="text" id="event_id" name="event_id" required />
            <button type="submit">Crear video</button>
        </form>

        <p>Ejemplo: igepn2026ffnc</p>
        <p>Si el video de ese evento ya está en proceso, se reutilizará el ticket activo.</p>
    </body>
    </html>
    """

@app.get("/ui/create")
def ui_create_ticket(request: Request, event_id: str = Query(..., min_length=1)):
    event_id_norm = normalize_event_id(event_id)

    existing = get_ticket_status_by_id(event_id_norm, TICKETS_DIR, EVENTS_DIR)
    if existing and existing.get("status") in ("pending", "queued", "processing"):
        ticket_id = existing["ticket_id"]
    else:
        ticket_id = start_video_job(
            event_id=event_id_norm,
            artifacts_dir=ARTIFACTS_DIR,
            events_dir=EVENTS_DIR,
            tickets_dir=TICKETS_DIR,
            semaphore=_JOB_SEMAPHORE,
        )

    view_url = request.url_for("view_ticket", ticket_id=ticket_id)
    return RedirectResponse(url=str(view_url), status_code=302)


@app.get("/tickets", response_model=CreateTicketResponse)
def create_ticket(
    request: Request,
    event_id: str = Query(..., min_length=1),
) -> CreateTicketResponse:
    """
    Create (or deduplicate) a ticket via GET.

    Example:
      GET /tickets?event_id=igepn2016hnmu
    """
    logger.info("/tickets requested: event_id=%s", event_id)
    event_id_norm = normalize_event_id(event_id)
    logger.info("event_id normalized: raw=%s normalized=%s", event_id, event_id_norm)

    # Fast path: if there is already an active ticket for this event, return it (no new job).
    existing = get_ticket_status_by_id(event_id_norm, TICKETS_DIR, EVENTS_DIR)
    if existing and existing.get("status") in ("pending", "queued", "processing"):
        status_url = str(request.url_for("get_ticket_status", ticket_id=existing["ticket_id"]))
        logger.info("deduplicated request: event_id=%s ticket_id=%s status=%s", event_id_norm, existing.get("ticket_id"), existing.get("status"))
        return CreateTicketResponse(
            ticket_id=existing["ticket_id"],
            status=existing["status"],
            status_url=status_url,
            deduplicated=True,
        )

    # Otherwise, create a new ticket and attempt to start the job.
    logger.info("creating new ticket: event_id=%s", event_id_norm)
    ticket_id = start_video_job(
        event_id=event_id_norm,
        artifacts_dir=ARTIFACTS_DIR,
        events_dir=EVENTS_DIR,
        tickets_dir=TICKETS_DIR,
        semaphore=_JOB_SEMAPHORE,
    )

    logger.info("ticket created: event_id=%s ticket_id=%s", event_id_norm, ticket_id)
    status_url = str(request.url_for("get_ticket_status", ticket_id=ticket_id))
    st = get_ticket_status_by_id(event_id_norm, TICKETS_DIR, EVENTS_DIR, ticket_id_hint=ticket_id)
    status = (st or {}).get("status", "queued")
    logger.info("create_ticket response: event_id=%s ticket_id=%s status=%s status_url=%s", event_id_norm, ticket_id, status, status_url)
    return CreateTicketResponse(ticket_id=ticket_id, status=status, status_url=status_url, deduplicated=False)


@app.get("/tickets/{ticket_id}", response_model=TicketStatus, name="get_ticket_status")
def get_ticket_status(ticket_id: str) -> TicketStatus:
    """
    Read ticket status by ticket_id.
    """
    logger.info("/tickets/%s requested", ticket_id)
    p = (TICKETS_DIR / ticket_id / "status.json").resolve()
    try:
        p.relative_to(TICKETS_DIR)
    except ValueError as e:
        logger.warning("invalid ticket_id path traversal attempt: %s", ticket_id)
        raise HTTPException(status_code=400, detail="invalid ticket_id") from e

    if not p.exists():
        logger.info("ticket not found: %s", ticket_id)
        raise HTTPException(status_code=404, detail="ticket not found")

    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        logger.exception("corrupted ticket status.json for ticket_id=%s", ticket_id)
        raise HTTPException(status_code=500, detail="corrupted ticket status") from e

    logger.info("ticket status read: ticket_id=%s status=%s", ticket_id, data.get("status"))

    return TicketStatus(**data)

@app.get("/tickets/{ticket_id}/video")
def get_ticket_video(ticket_id: str):
    try:
        video_path = resolve_ticket_video_path(
            ticket_id=ticket_id,
            tickets_dir=TICKETS_DIR,
            artifacts_dir=ARTIFACTS_DIR,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        # Not ready / error states
        raise HTTPException(status_code=409, detail=str(e)) from e

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=video_path.name,
    )


@app.get("/tickets/{ticket_id}/view", response_class=HTMLResponse, name="view_ticket")
def view_ticket(ticket_id: str):
    p = (TICKETS_DIR / ticket_id / "status.json").resolve()

    try:
        p.relative_to(TICKETS_DIR)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="invalid ticket_id") from e

    if not p.exists():
        raise HTTPException(status_code=404, detail="ticket not found")

    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail="corrupted ticket status") from e

    status = data.get("status")
    event_id = data.get("event_id")
    created_at = data.get("created_at")
    started_at = data.get("started_at")
    finished_at = data.get("finished_at")
    message = data.get("message")

    status_url = f"/tickets/{ticket_id}"
    video_url = f"/tickets/{ticket_id}/video"

    auto_refresh = ""
    if status in ("queued", "processing"):
        auto_refresh = '<meta http-equiv="refresh" content="5">'

    html = f"""
    <html>
    <head>
        <title>Ticket {ticket_id}</title>
        {auto_refresh}
    </head>
    <body>
        <h2>Ticket {ticket_id}</h2>

        <p><b>Event ID:</b> {event_id}</p>
        <p><b>Status:</b> {status}</p>
        <p><b>Created:</b> {created_at}</p>
        <p><b>Started:</b> {started_at}</p>
        <p><b>Finished:</b> {finished_at}</p>

        <hr>

        <p><a href="{status_url}">Ver status JSON</a></p>
        <p><a href="/ui">Volver al inicio</a></p>
    """

    if status == "done":
        html += f'<p><a href="{video_url}">Descargar video</a></p>'
    elif status == "queued":
        html += "<p>El ticket está en cola.</p>"
    elif status == "processing":
        html += "<p>El video se está generando. Esta página se actualizará automáticamente.</p>"
    elif status == "error":
        html += f"<p><b>Error:</b> {message}</p>"

    html += """
    </body>
    </html>
    """

    return html