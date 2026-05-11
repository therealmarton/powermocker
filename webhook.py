"""FastAPI service that streams pre-generated CSV to the energy-community backend.

POST /start  -> kicks off a background streaming thread
GET  /status -> current progress
POST /stop   -> cancel an in-flight stream
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Optional

import pandas as pd
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
CSV_PATH = Path(
    os.environ.get("POWERMOCKER_CSV", str(ROOT / "haz_adatok" / "osszes_haz_adat.csv"))
)
BACKEND_URL = os.environ.get(
    "BACKEND_WEBHOOK_URL", "http://backend:8000/webhook/powermocker"
)
CHUNK_SIZE = 576  # 6 houses * 96 quarter-hours = 1 day

app = FastAPI(title="PowerMocker Webhook Streamer", version="0.1.0")


class StartRequest(BaseModel):
    days: int = Field(default=0, ge=0, description="0 = stream the full CSV")
    delay_ms: int = Field(default=1000, ge=0, description="Pause between day-batches")
    drop_first: bool = Field(default=False, description="Call /api/data-drop before streaming")


class StreamState:
    def __init__(self) -> None:
        self.lock = Lock()
        self.stop_event = Event()
        self.thread: Optional[Thread] = None
        self.running = False
        self.total_days = 0
        self.current_day = 0
        self.sent = 0
        self.inserted = 0
        self.error: Optional[str] = None


state = StreamState()


def _drop_backend_data() -> None:
    drop_url = BACKEND_URL.replace("/webhook/powermocker", "/api/data-drop")
    requests.post(drop_url, timeout=30).raise_for_status()


def _stream_loop(req: StartRequest) -> None:
    try:
        df = pd.read_csv(CSV_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).apply(lambda x: x.isoformat())
        records = df.to_dict("records")
        if req.days > 0:
            records = records[: req.days * CHUNK_SIZE]

        with state.lock:
            state.total_days = (len(records) + CHUNK_SIZE - 1) // CHUNK_SIZE

        if req.drop_first:
            _drop_backend_data()

        for i in range(0, len(records), CHUNK_SIZE):
            if state.stop_event.is_set():
                break
            chunk = records[i : i + CHUNK_SIZE]
            r = requests.post(
                BACKEND_URL,
                json={"type": "batch_update", "data": chunk},
                timeout=120,
            )
            r.raise_for_status()
            body = r.json()
            with state.lock:
                state.current_day += 1
                state.sent += body.get("received", len(chunk))
                state.inserted += body.get("inserted", 0)
            if state.stop_event.wait(req.delay_ms / 1000):
                break
    except Exception as exc:  # noqa: BLE001
        with state.lock:
            state.error = repr(exc)
    finally:
        with state.lock:
            state.running = False


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "backend": BACKEND_URL, "csv": str(CSV_PATH)}


@app.post("/start", status_code=202)
def start(req: StartRequest) -> dict:
    if not CSV_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail=f"CSV not found at {CSV_PATH}; run generator.py first",
        )
    with state.lock:
        if state.running:
            raise HTTPException(status_code=409, detail="Stream already running")
        state.stop_event.clear()
        state.running = True
        state.current_day = 0
        state.sent = 0
        state.inserted = 0
        state.error = None
        state.thread = Thread(target=_stream_loop, args=(req,), daemon=True)
        state.thread.start()
    return {"status": "started", "backend": BACKEND_URL, "request": req.model_dump()}


@app.post("/stop")
def stop() -> dict:
    with state.lock:
        if not state.running:
            return {"status": "not_running"}
        state.stop_event.set()
    return {"status": "stopping"}


@app.get("/status")
def status() -> dict:
    with state.lock:
        return {
            "running": state.running,
            "current_day": state.current_day,
            "total_days": state.total_days,
            "sent": state.sent,
            "inserted": state.inserted,
            "error": state.error,
        }
