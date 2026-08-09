"""Supabase (PostgREST) への簡易REST クライアント.

環境変数 SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY を使う。
service_role キーはRLSをバイパスするため、管理者のローカル実行やGitHub Actionsの
Secretsとしてのみ使用し、絶対にフロントエンド(GitHub Pages)には含めないこと。
"""
from __future__ import annotations

import os
from typing import Any

import requests


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"環境変数 {name} が設定されていません。SUPABASE_URL と "
            "SUPABASE_SERVICE_ROLE_KEY を設定してください。"
        )
    return value


def _headers() -> dict[str, str]:
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _rest_url(path: str) -> str:
    base = _env("SUPABASE_URL").rstrip("/")
    return f"{base}/rest/v1/{path}"


def get_points() -> list[dict[str, Any]]:
    resp = requests.get(_rest_url("points?select=*"), headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def insert_point(name: str, lat: float, lng: float, radius_m: int = 500, memo: str = "") -> dict[str, Any]:
    body = {"name": name, "lat": lat, "lng": lng, "radius_m": radius_m, "memo": memo}
    headers = {**_headers(), "Prefer": "return=representation"}
    resp = requests.post(_rest_url("points"), headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()[0]


def upsert_traffic_records(records: list[dict[str, Any]]) -> int:
    """point_id/observed_at/source が重複するレコードは無視して挿入する."""
    if not records:
        return 0
    headers = {
        **_headers(),
        "Prefer": "resolution=ignore-duplicates,return=representation",
    }
    url = _rest_url("traffic_records?on_conflict=point_id,observed_at,source")
    inserted = 0
    # 大量データでのリクエストサイズ肥大を避けるためチャンク単位で送る
    chunk_size = 500
    for i in range(0, len(records), chunk_size):
        chunk = records[i : i + chunk_size]
        resp = requests.post(url, headers=headers, json=chunk, timeout=60)
        resp.raise_for_status()
        inserted += len(resp.json())
    return inserted
