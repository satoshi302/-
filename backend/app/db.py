import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "traffic.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    radius_m INTEGER NOT NULL DEFAULT 500,
    memo TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS traffic_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    point_id INTEGER NOT NULL REFERENCES points(id) ON DELETE CASCADE,
    observed_at TEXT NOT NULL,
    lat REAL,
    lng REAL,
    road_type TEXT,
    volume_up INTEGER,
    volume_down INTEGER,
    source TEXT NOT NULL DEFAULT 'live',
    raw_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(point_id, observed_at, source, lat, lng)
);

CREATE INDEX IF NOT EXISTS idx_traffic_point_time
    ON traffic_records(point_id, observed_at);
"""


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
