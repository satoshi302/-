from fastapi import APIRouter, HTTPException

from ..db import get_conn
from ..models import PointCreate, PointOut

router = APIRouter(prefix="/api/points", tags=["points"])


@router.get("", response_model=list[PointOut])
def list_points():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM points ORDER BY id").fetchall()
        return [dict(r) for r in rows]


@router.post("", response_model=PointOut)
def create_point(point: PointCreate):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO points (name, lat, lng, radius_m, memo) VALUES (?, ?, ?, ?, ?)",
            (point.name, point.lat, point.lng, point.radius_m, point.memo),
        )
        row = conn.execute("SELECT * FROM points WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)


@router.delete("/{point_id}")
def delete_point(point_id: int):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM points WHERE id = ?", (point_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="地点が見つかりません")
    return {"ok": True}
