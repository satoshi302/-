"""登録済みの全地点についてJARTIC APIから最新データを取得しDBへ保存する.

GitHub Actionsなどのスケジューラから定期実行することで、JARTICが約1か月で消してしまう
データを取りこぼさずに蓄積していく。単体でも `python scripts/fetch_all.py` で実行可能。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import jartic_client  # noqa: E402
from app.db import get_conn, init_db  # noqa: E402
from app.storage import insert_records  # noqa: E402


def main() -> None:
    init_db()
    with get_conn() as conn:
        points = [dict(r) for r in conn.execute("SELECT * FROM points").fetchall()]

    if not points:
        print("登録された地点がありません。先にアプリから地点を登録してください。")
        return

    for p in points:
        try:
            records = jartic_client.fetch_traffic_volume(
                lat=p["lat"], lng=p["lng"], radius_m=p["radius_m"], minutes_back=180
            )
        except Exception as e:
            print(f"[WARN] {p['name']}: 取得失敗 ({e})")
            continue

        with get_conn() as conn:
            inserted = insert_records(conn, p["id"], "live", records)
        print(f"{p['name']}: fetched={len(records)} inserted={inserted}")


if __name__ == "__main__":
    main()
