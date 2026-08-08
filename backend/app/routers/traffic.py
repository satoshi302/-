from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile

from .. import jartic_client
from ..db import get_conn
from ..importer import parse_archive_csv
from ..models import FetchResult
from ..storage import insert_records

router = APIRouter(prefix="/api/traffic", tags=["traffic"])


@router.post("/fetch/{point_id}", response_model=FetchResult)
def fetch_live(point_id: int, minutes_back: int = 60):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM points WHERE id = ?", (point_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="地点が見つかりません")

        try:
            records = jartic_client.fetch_traffic_volume(
                lat=row["lat"], lng=row["lng"], radius_m=row["radius_m"], minutes_back=minutes_back
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"JARTIC APIの取得に失敗しました: {e}")

        inserted = insert_records(conn, point_id, "live", records)

    return FetchResult(
        point_id=point_id,
        fetched=len(records),
        inserted=inserted,
        message="取得完了",
    )


@router.post("/import/{point_id}", response_model=FetchResult)
async def import_archive(point_id: int, file: UploadFile = File(...)):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM points WHERE id = ?", (point_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="地点が見つかりません")

        content = await file.read()
        records = parse_archive_csv(content, default_lat=row["lat"], default_lng=row["lng"])
        if not records:
            raise HTTPException(status_code=400, detail="CSVから有効なデータを読み取れませんでした")

        inserted = insert_records(conn, point_id, "archive", records)

    return FetchResult(
        point_id=point_id,
        fetched=len(records),
        inserted=inserted,
        message=f"{file.filename} を取り込みました",
    )


@router.get("/compare")
def compare(point_id: int, current_start: str, current_end: str, past_start: str, past_end: str):
    def _load(start: str, end: str) -> list[dict]:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT observed_at, volume_up, volume_down FROM traffic_records
                WHERE point_id = ? AND date(observed_at) BETWEEN date(?) AND date(?)
                """,
                (point_id, start, end),
            ).fetchall()
            return [dict(r) for r in rows]

    def _aggregate(rows: list[dict]):
        by_hour: dict[int, list[int]] = defaultdict(list)
        by_date: dict[str, list[int]] = defaultdict(list)
        for r in rows:
            try:
                dt = datetime.fromisoformat(r["observed_at"])
            except ValueError:
                continue
            total = (r["volume_up"] or 0) + (r["volume_down"] or 0)
            by_hour[dt.hour].append(total)
            by_date[dt.date().isoformat()].append(total)

        hourly_avg = {h: round(sum(v) / len(v), 1) for h, v in by_hour.items()}
        daily_avg = {d: round(sum(v) / len(v), 1) for d, v in by_date.items()}
        return {"hourly_avg": hourly_avg, "daily_avg": daily_avg, "sample_count": len(rows)}

    current_rows = _load(current_start, current_end)
    past_rows = _load(past_start, past_end)

    return {
        "point_id": point_id,
        "current": _aggregate(current_rows),
        "past": _aggregate(past_rows),
    }


@router.get("/records/{point_id}")
def list_records(point_id: int, limit: int = 500):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, observed_at, road_type, volume_up, volume_down, source
            FROM traffic_records WHERE point_id = ?
            ORDER BY observed_at DESC LIMIT ?
            """,
            (point_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
