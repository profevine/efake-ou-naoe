from __future__ import annotations
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .models import AnalyzeRequest, AnalyzeResult, HistoryItem
from . import database, analyzer

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db()
    yield


app = FastAPI(title="eFake ou Não É?", lifespan=lifespan)

app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR / "static")),
    name="static",
)


@app.get("/", response_class=FileResponse)
async def index():
    return FileResponse(str(FRONTEND_DIR / "templates" / "index.html"))


@app.post("/analyze", response_model=AnalyzeResult)
async def analyze_news(body: AnalyzeRequest):
    if not body.input.strip():
        raise HTTPException(status_code=422, detail="O campo 'input' não pode ser vazio.")
    return await analyzer.analyze(body.input)


@app.get("/history", response_model=list[HistoryItem])
async def history():
    rows = await database.get_history()
    return rows


@app.get("/health")
async def health():
    return {"status": "ok"}
