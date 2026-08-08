"""Compusophia等が配布するJARTIC形式の過去データ(CSV)を取り込むインポーター.

Compusophia (https://www.compusophia.com/en/notes/1) はJARTICが毎月消してしまう
断面交通量オープンデータをアーカイブして配布しているノート。ダウンロードした
CSVをこのモジュールでDBに取り込み、過去の8月/9月データとして比較に使う。

CSVの列名はJARTIC生データに準じる想定(時間コード/道路種別/上り交通量/下り交通量 等)。
実際にダウンロードしたファイルの列名が異なる場合は COLUMN_ALIASES を調整すること。
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any

COLUMN_ALIASES = {
    "time": ["時間コード", "observed_at", "time_code", "計測時間"],
    "lat": ["緯度", "lat", "latitude"],
    "lng": ["経度", "lng", "longitude"],
    "road_type": ["道路種別", "road_type"],
    "volume_up": ["上り交通量", "上り小型", "volume_up"],
    "volume_down": ["下り交通量", "下り小型", "volume_down"],
}


def _resolve_columns(fieldnames: list[str]) -> dict[str, str | None]:
    resolved: dict[str, str | None] = {}
    for key, aliases in COLUMN_ALIASES.items():
        resolved[key] = next((a for a in aliases if a in fieldnames), None)
    return resolved


def _parse_time(raw: str) -> str:
    raw = raw.strip()
    for fmt in ("%Y%m%d%H%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except ValueError:
            continue
    try:
        return datetime.strptime(raw[:12], "%Y%m%d%H%M").isoformat()
    except ValueError:
        return raw


def parse_archive_csv(content: bytes, default_lat: float, default_lng: float) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    cols = _resolve_columns(reader.fieldnames)

    records: list[dict[str, Any]] = []
    for row in reader:
        raw_time = row.get(cols["time"]) if cols["time"] else None
        if not raw_time:
            continue
        try:
            lat = float(row[cols["lat"]]) if cols["lat"] else default_lat
        except (TypeError, ValueError):
            lat = default_lat
        try:
            lng = float(row[cols["lng"]]) if cols["lng"] else default_lng
        except (TypeError, ValueError):
            lng = default_lng

        records.append(
            {
                "observed_at": _parse_time(raw_time),
                "lat": lat,
                "lng": lng,
                "road_type": row.get(cols["road_type"]) if cols["road_type"] else None,
                "volume_up": _to_int(row.get(cols["volume_up"])) if cols["volume_up"] else None,
                "volume_down": _to_int(row.get(cols["volume_down"])) if cols["volume_down"] else None,
                "raw_json": json.dumps(row, ensure_ascii=False),
            }
        )
    return records


def _to_int(v: Any) -> int | None:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None
