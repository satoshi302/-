# 引越し渋滞情報 比較ツール

引越し先の検討にあたり、登録した地点まわりの交通量を「過去(去年など)」と
「これから(現在〜引越し予定の8月・9月)」で比較するための家族用ツールです。

## データソース(無料)

- **[JARTIC 交通量オープンデータAPI](https://www.jartic-open-traffic.org/)**
  全国の断面交通量(5分毎)をリアルタイムに近い形で取得できますが、公開されるのは
  **直近およそ1か月分のみ**で、月次で古いデータが消去されます。そのため本ツールは
  定期的にAPIを叩いてデータをDBに蓄積し、「これから」の実績を積み上げていきます。
- **[Compusophia](https://www.compusophia.com/en/notes/1)**
  JARTICが消してしまう過去データをアーカイブして配布しているノートです。
  ここからダウンロードしたCSVを本ツールに取り込むことで、過去(去年の8月・9月など)
  のデータとして比較に使えます。

## 構成

```
backend/   FastAPI + SQLite のバックエンド
  app/
    jartic_client.py  JARTIC APIから地点周辺の交通量を取得
    importer.py        Compusophia等のアーカイブCSVを取り込み
    routers/            地点登録・データ取得・比較API
  scripts/fetch_all.py  登録済み全地点のデータをJARTIC APIから取得するバッチ
  data/traffic.db        SQLiteデータベース(自動生成)
frontend/  地点登録・データ収集・比較グラフ表示のシンプルなWeb UI
.github/workflows/fetch-traffic.yml
  GitHub Actionsで3時間ごとに自動でデータ取得し、DBをコミットする無料の定期実行
```

## セットアップ

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

ブラウザで `http://localhost:8000` を開くとダッシュボードが表示されます。

## 使い方

1. **地点登録**: 現在の家、新居候補、通勤ルート上の地点などを緯度経度で登録します。
   緯度経度はGoogleマップで地点を右クリックするとコピーできます。
2. **データ収集**:
   - 「今のデータを取得」で、その時点のJARTICデータを1件手動取得できます。
   - 継続的な蓄積には GitHub Actions (`.github/workflows/fetch-traffic.yml`) を使います。
     このリポジトリをGitHubにpushしてActionsを有効にすると、3時間ごとに自動でデータを
     取得し `backend/data/traffic.db` をコミットしてくれます(完全無料枠で動作)。
   - 過去データは Compusophia からダウンロードしたCSVを「過去データ取込」からアップロード
     してください。
3. **比較**: 地点と「これからの期間」「過去の期間」を選んで比較すると、
   時間帯別・日別の平均交通量グラフが表示されます。

## 既知の制約・要確認事項

- JARTIC APIのプロパティ名(道路種別・時間コード・上り/下り交通量など)は
  `backend/app/jartic_client.py` の `CANDIDATE_*_KEYS` に候補を列挙して吸収する形に
  していますが、実際のレスポンスで名称が異なる場合は調整が必要です。生のレスポンスは
  `raw_json` 列に必ず保存されるので、そこから正しいキー名を確認できます。
- Compusophiaのアーカイブファイルの列名も同様に `backend/app/importer.py` の
  `COLUMN_ALIASES` で吸収していますが、実ファイルに合わせて調整してください。
- 断面交通量データは主要道路のセンサー設置箇所のみが対象のため、登録地点の近くに
  センサーがない場合はデータが取得できないことがあります(`radius_m` を広げて調整)。
