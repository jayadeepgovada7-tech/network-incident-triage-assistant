from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from src.config import GEMINI_MODEL, GEMINI_API_KEY
from src.data_loader import load_devices, load_topology, load_samples, load_runbooks
from src.inbox import ingest, snapshot, clear
from src.triage import triage

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"

app = FastAPI(title="PS07 Network Incident Triage")


class TriageRequest(BaseModel):
    alerts: list = []


@app.get("/health")
def health():
    return {"status": "ok", "track": "PS07"}


@app.get("/api/status")
def api_status():
    box = snapshot()
    return {
        "backend": "online",
        "model": GEMINI_MODEL,
        "runbooks": len(load_runbooks()),
        "gemini_key": bool(GEMINI_API_KEY),
        "inbox": box["count"],
        "ingest": "/api/ingest",
    }


@app.get("/")
def home():
    return FileResponse(FRONTEND / "index.html")


@app.get("/api/devices")
def api_devices():
    return {"devices": load_devices()}


@app.get("/api/topology")
def api_topology():
    return load_topology()


@app.get("/api/runbooks")
def api_runbooks():
    books = load_runbooks()
    return {
        "count": len(books),
        "runbooks": [
            {"id": b["id"], "title": b["title"], "filename": b["filename"]}
            for b in books
        ],
    }


@app.get("/api/samples")
def api_samples():
    return load_samples()


@app.post("/api/triage")
def api_triage(req: TriageRequest):
    return triage(req.alerts)


@app.get("/api/triage/fibre_cut")
def api_fibre_cut():
    return triage(load_samples()["fibre_cut"])


@app.get("/api/triage/unknown_fault")
def api_unknown():
    return triage(load_samples()["unknown_fault"])


@app.get("/api/triage/auth_noise")
def api_auth():
    return triage(load_samples()["auth_noise"])


@app.get("/api/triage/two_sites")
def api_two_sites():
    return triage(load_samples()["two_sites"])


@app.post("/api/ingest")
def api_ingest(payload: Any = Body(...)):
    return ingest(payload)


@app.get("/api/inbox")
def api_inbox():
    return snapshot()


@app.delete("/api/inbox")
def api_inbox_clear():
    return clear()


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")