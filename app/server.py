"""Local web altar. Nothing here calls a remote model."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.remember import MODEL, ollama_status, speak
from app.sample import ensure_sample
from app.scan import ScanError, read_grave, scan_folder

WEB = Path(__file__).resolve().parents[1] / "web"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_sample()
    yield


app = FastAPI(title="Ofrenda", lifespan=lifespan)


class PathBody(BaseModel):
    path: str


@app.get("/api/health")
def health():
    return ollama_status(MODEL)


@app.get("/api/sample")
def sample():
    grave = read_grave(ensure_sample())
    return {"graves": [grave], "truncated": False}


@app.post("/api/altar")
def altar(body: PathBody):
    try:
        graves, truncated = scan_folder(body.path)
    except ScanError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"graves": graves, "truncated": truncated}


@app.post("/api/remembrance")
def remembrance(body: PathBody):
    try:
        return speak(body.path)
    except ScanError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/assets", StaticFiles(directory=WEB), name="assets")
