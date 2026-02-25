from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import uuid
import json
import os

from iganima.api.services.runner import run_ticket
import threading

# -----------------------------------------------------------------------------
# Configuración básica
# -----------------------------------------------------------------------------

BASE_TMP_DIR = Path(os.environ.get("IGSISMANI_TMP_DIR", "./tmp"))
BASE_TMP_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Modelos
# -----------------------------------------------------------------------------

class TicketRequest(BaseModel):
    event_id: str
    iganima_config: str


class TicketStatus(BaseModel):
    ticket: str
    status: str
    message: str
    started_at: str
    updated_at: str


# -----------------------------------------------------------------------------
# App FastAPI
# -----------------------------------------------------------------------------

app = FastAPI(
    title="IGSISMANI API",
    description="Servicio de generación de videos sísmicos",
    version="0.1.0",
)


# -----------------------------------------------------------------------------
# Utilidades internas
# -----------------------------------------------------------------------------

def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")


def ticket_dir(ticket_id: str) -> Path:
    return BASE_TMP_DIR / ticket_id


def status_file(ticket_id: str) -> Path:
    return ticket_dir(ticket_id) / "status.json"


def write_status(ticket_id: str, status: str, message: str):
    data = {
        "ticket": ticket_id,
        "status": status,
        "message": message,
        "started_at": now_iso(),
        "updated_at": now_iso(),
    }
    status_file(ticket_id).write_text(json.dumps(data, indent=2))


def read_status(ticket_id: str):
    path = status_file(ticket_id)
    if not path.exists():
        raise FileNotFoundError
    return json.loads(path.read_text())


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tickets")
def create_ticket(req: TicketRequest):
    """
    Crea un ticket de generación de video.
    (En esta fase NO ejecuta run_igsismani.py todavía)
    """
    ticket_id = str(uuid.uuid4())
    tdir = ticket_dir(ticket_id)
    tdir.mkdir(parents=True, exist_ok=False)

    write_status(
        ticket_id,
        status="pending",
        message=f"Ticket creado para evento {req.event_id}",
    )

    # Guardar request original para trazabilidad
    #(tdir / "request.json").write_text(req.json(indent=2))
    import json

    (tdir / "request.json").write_text(
        json.dumps(req.model_dump(), indent=2)
    )

    thread = threading.Thread(
        target=run_ticket,
        args=(tdir, req.event_id, req.iganima_config),
        daemon=True,
    )
    thread.start()

    return {
        "ticket": ticket_id,
        "status": "processing",
    }


@app.get("/tickets/{ticket_id}")
def get_ticket_status(ticket_id: str):
    try:
        return read_status(ticket_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
