"""JARTIC/国交省 交通量オープンデータAPI クライアント.

エンドポイント: https://api.jartic-open-traffic.org/geoserver
WFS 2.0.0 GetFeature 形式, typeNames=t_travospublic_measure_5m (5分毎断面交通量).

JARTICは「直近約1か月分」のみを公開し月次で古いデータを消去するため、このスクリプトを
定期実行(GitHub Actions等)してSupabaseへ蓄積していくことで時系列データを育てる想定。

フィールド名(道路種別/時間コード/上り下り交通量など)は公開仕様書の表記ゆれがあるため、
既知の候補キーを複数試しつつ、生のpropertiesも常にraw_jsonとして保存する。実データで
名称が違えば CANDIDATE_KEYS を調整すること。
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import Any

import requests

ENDPOINT = "https://api.jartic-open-traffic.org/geoserver"
TYPE_NAME = "t_travospublic_measure_5m"

CANDIDATE_TIME_KEYS = ["時間コード", "observationTime", "OBS_TIME", "time_code"]
CANDIDATE_ROAD_TYPE_KEYS = ["道路種別", "road_type", "ROAD_TYPE"]
CANDIDATE_UP_KEYS = ["上り交通量", "上り小型", "up_volume", "UP_VOLUME"]
CANDIDATE_DOWN_KEYS = ["下り交通量", "下り小型", "down_volume", "DOWN_VOLUME"]


def _first_present(props: dict[str, Any], keys: list[str]) -> Any:
    for k in keys:
        if k in props and props[k] not in (None, ""):
            return props[k]
    return None


def bbox_from_point(lat: float, lng: float, radius_m: int) -> tuple[float, float, float, float]:
    dlat = radius_m / 111_000
    dlng = radius_m / (111_000 * max(math.cos(math.radians(lat)), 0.01))
    return (lng - dlng, lat - dlat, lng + dlng, lat + dlat)


def fetch_traffic_volume(
    lat: float,
    lng: float,
    radius_m: int = 500,
    minutes_back: int = 1440,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """指定地点周辺の直近 minutes_back 分の断面交通量データを取得する(既定: 24時間分)."""
    min_x, min_y, max_x, max_y = bbox_from_point(lat, lng, radius_m)

    now = datetime.utcnow() + timedelta(hours=9)  # JST概算
    start = now - timedelta(minutes=minutes_back)
    time_start = start.strftime("%Y%m%d%H%M")
    time_end = now.strftime("%Y%m%d%H%M")

    cql_filter = (
        f"BBOX(mesh_geom,{min_x},{min_y},{max_x},{max_y},'EPSG:4326') "
        f"AND 時間コード BETWEEN {time_start} AND {time_end}"
    )

    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": TYPE_NAME,
        "srsName": "EPSG:4326",
        "outputFormat": "application/json",
        "cql_filter": cql_filter,
    }

    resp = requests.get(ENDPOINT, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    records: list[dict[str, Any]] = []
    for feature in data.get("features", []):
        props = feature.get("properties", {}) or {}
        geom = feature.get("geometry", {}) or {}
        coords = _extract_first_coord(geom)

        raw_time = _first_present(props, CANDIDATE_TIME_KEYS)
        observed_at = _parse_time_code(raw_time) if raw_time else now.isoformat()

        records.append(
            {
                "observed_at": observed_at,
                "lat": coords[1] if coords else lat,
                "lng": coords[0] if coords else lng,
                "road_type": _first_present(props, CANDIDATE_ROAD_TYPE_KEYS),
                "volume_up": _to_int(_first_present(props, CANDIDATE_UP_KEYS)),
                "volume_down": _to_int(_first_present(props, CANDIDATE_DOWN_KEYS)),
                "raw_json": json.dumps(props, ensure_ascii=False),
            }
        )
    return records


def _extract_first_coord(geom: dict[str, Any]) -> tuple[float, float] | None:
    coords = geom.get("coordinates")
    if not coords:
        return None
    if isinstance(coords[0], (list, tuple)):
        return tuple(coords[0])  # type: ignore[return-value]
    return tuple(coords)  # type: ignore[return-value]


def _parse_time_code(raw: Any) -> str:
    s = str(raw)
    try:
        return datetime.strptime(s[:12], "%Y%m%d%H%M").isoformat()
    except ValueError:
        return s


def _to_int(v: Any) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
