"""traffic_records への共通挿入処理."""
from __future__ import annotations

import sqlite3


def insert_records(conn: sqlite3.Connection, point_id: int, source: str, records: list[dict]) -> int:
    inserted = 0
    for r in records:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO traffic_records
                (point_id, observed_at, lat, lng, road_type, volume_up, volume_down, source, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                point_id,
                r["observed_at"],
                r.get("lat"),
                r.get("lng"),
                r.get("road_type"),
                r.get("volume_up"),
                r.get("volume_down"),
                source,
                r.get("raw_json"),
            ),
        )
        inserted += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
    return inserted
