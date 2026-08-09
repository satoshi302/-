"""Compusophiaなどからダウンロードした過去データCSVをSupabaseへ取り込む管理者用CLI.

使い方:
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
        python scripts/import_archive.py <point_id> path/to/archive.csv
"""
import argparse
import sys

import supabase_client
from archive_csv import parse_archive_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="過去データCSVをSupabaseへ取り込む")
    parser.add_argument("point_id", type=int, help="対象地点のID")
    parser.add_argument("csv_path", help="CSVファイルのパス")
    args = parser.parse_args()

    points = {p["id"]: p for p in supabase_client.get_points()}
    point = points.get(args.point_id)
    if not point:
        print(f"地点ID {args.point_id} が見つかりません。", file=sys.stderr)
        sys.exit(1)

    with open(args.csv_path, "rb") as f:
        content = f.read()

    records = parse_archive_csv(content, default_lat=point["lat"], default_lng=point["lng"])
    if not records:
        print("CSVから有効なデータを読み取れませんでした。", file=sys.stderr)
        sys.exit(1)

    for r in records:
        r["point_id"] = args.point_id
        r["source"] = "archive"

    inserted = supabase_client.upsert_traffic_records(records)
    print(f"{point['name']}: 読取={len(records)}件 / 新規保存={inserted}件")


if __name__ == "__main__":
    main()
