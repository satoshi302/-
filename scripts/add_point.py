"""地点をSupabaseに登録する管理者用CLI.

使い方:
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
        python scripts/add_point.py "新居候補A" 35.6812 139.7671 --radius 500 --memo "駅から徒歩5分"
"""
import argparse

import supabase_client


def main() -> None:
    parser = argparse.ArgumentParser(description="地点をSupabaseに登録する")
    parser.add_argument("name", help="地点名")
    parser.add_argument("lat", type=float, help="緯度")
    parser.add_argument("lng", type=float, help="経度")
    parser.add_argument("--radius", type=int, default=500, help="JARTIC取得範囲(m)")
    parser.add_argument("--memo", default="", help="メモ")
    args = parser.parse_args()

    point = supabase_client.insert_point(args.name, args.lat, args.lng, args.radius, args.memo)
    print(f"登録しました: id={point['id']} name={point['name']}")


if __name__ == "__main__":
    main()
