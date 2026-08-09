"""登録済みの全地点についてJARTIC APIから直近24時間分のデータを取得しSupabaseへ保存する.

GitHub Actionsから1日1回実行する想定(README参照)。単体でも
`SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python scripts/fetch_daily.py` で実行可能。
"""
import jartic_client
import supabase_client


def main() -> None:
    points = supabase_client.get_points()
    if not points:
        print("登録された地点がありません。先に scripts/add_point.py で地点を登録してください。")
        return

    for p in points:
        try:
            records = jartic_client.fetch_traffic_volume(
                lat=p["lat"], lng=p["lng"], radius_m=p["radius_m"], minutes_back=1440
            )
        except Exception as e:
            print(f"[WARN] {p['name']}: 取得失敗 ({e})")
            continue

        for r in records:
            r["point_id"] = p["id"]

        inserted = supabase_client.upsert_traffic_records(records)
        print(f"{p['name']}: fetched={len(records)} inserted={inserted}")


if __name__ == "__main__":
    main()
