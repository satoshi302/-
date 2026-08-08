from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routers import points, traffic

app = FastAPI(title="引越し渋滞情報 比較ツール")

init_db()

app.include_router(points.router)
app.include_router(traffic.router)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
