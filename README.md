# 引越し渋滞情報 比較ツール

引越し先の検討にあたり、登録した地点まわりの交通量を「過去(去年など)」と
「これから(現在〜引越し予定の8月・9月)」で比較するための家族用ツールです。

## 構成

- **フロントエンド**: `frontend/` — GitHub Pagesで配信する静的サイト(閲覧専用)。
  [Supabase JS](https://supabase.com/docs/reference/javascript) でDBを直接読み取り、
  比較グラフ(時間帯別・日別)を表示します。
- **データベース**: [Supabase](https://supabase.com/) (Postgres, 無料枠)
  - `points`: 登録地点(名前・緯度経度・取得範囲)
  - `traffic_records`: 交通量データ(JARTIC取得分 / 過去アーカイブ取込分)
  - RLS(Row Level Security)で **読み取りは誰でも可、書き込みは管理者のみ**
    (`service_role`キーを使うスクリプト経由)に制限しています。
- **管理スクリプト**: `scripts/` — 地点登録・過去データ取込・日次データ収集を行う
  ローカル実行用のPythonスクリプト(管理者のみが実行)。
- **自動データ収集**: `.github/workflows/fetch-traffic.yml` — GitHub Actionsで
  毎日1回、登録済み全地点のJARTICデータを取得してSupabaseに蓄積します。
- **自動デプロイ**: `.github/workflows/deploy-pages.yml` — `frontend/`をGitHub Pagesへ
  自動デプロイします。

## データソース(無料)

- **[JARTIC 交通量オープンデータAPI](https://www.jartic-open-traffic.org/)**
  全国の断面交通量(5分毎)を取得できますが、公開されるのは**直近およそ1か月分のみ**で、
  月次で古いデータが消去されます。そのため`fetch-traffic.yml`が毎日Supabaseへ
  蓄積していくことで「これから」の実績を積み上げます。
- **[Compusophia](https://www.compusophia.com/en/notes/1)**
  JARTICが消してしまう過去データをアーカイブして配布しているノートです。
  ダウンロードしたCSVを`scripts/import_archive.py`でSupabaseに取り込み、
  過去(去年の8月・9月など)のデータとして比較に使います。

## セットアップ

### 1. Supabaseのキーを控える

Supabaseダッシュボード → 対象プロジェクト → **Project Settings → API** から
`service_role`キー(secret)を控えてください。**このキーは絶対にリポジトリや
フロントエンドにコミットしないでください**(RLSをバイパスしてしまいます)。

### 2. GitHub Secretsを設定する

リポジトリの **Settings → Secrets and variables → Actions** で以下を登録します。

| Secret名 | 値 |
|---|---|
| `SUPABASE_URL` | `https://bclqrhkhxjeieiomtjrc.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | 手順1で控えたservice_roleキー |

これで`fetch-traffic.yml`が毎日06:00 JSTにJARTICデータを取得しSupabaseへ保存します
(手動実行は Actions タブから `workflow_dispatch` でも可能)。

### 3. GitHub Pagesを有効にする

リポジトリの **Settings → Pages** で、Source を **GitHub Actions** に設定してください。
`main`ブランチに`frontend/`配下の変更がpushされると自動でデプロイされます
(初回は`deploy-pages.yml`を手動実行 = `workflow_dispatch` でも公開できます)。

### 4. 地点を登録する(管理者のみ)

```bash
cd scripts
pip install -r requirements.txt
export SUPABASE_URL=https://bclqrhkhxjeieiomtjrc.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=<service_roleキー>

python add_point.py "現在の家" 35.6812 139.7671 --radius 500
python add_point.py "新居候補A" 35.4437 139.6380 --radius 500 --memo "駅から徒歩5分"
```

### 5. 過去データを取り込む(管理者のみ)

[Compusophia](https://www.compusophia.com/en/notes/1) からダウンロードしたCSVを
取り込みます(`<point_id>`は`add_point.py`実行時に表示されるID)。

```bash
python import_archive.py <point_id> path/to/archive.csv
```

### 6. 今すぐ最新データを取得する(任意)

日次バッチを待たずに手動で取得したい場合:

```bash
python fetch_daily.py
```

## 使い方

GitHub PagesのURLを開き、地点と「これからの期間」「過去の期間」を選んで
「比較する」を押すと、時間帯別・日別の平均交通量グラフが表示されます。
地点の追加や過去データの取込は管理者が`scripts/`で行います(家族はダッシュボードの閲覧のみ)。

## 既知の制約・要確認事項

- JARTIC APIのプロパティ名(道路種別・時間コード・上り/下り交通量など)は
  `scripts/jartic_client.py`の`CANDIDATE_*_KEYS`に候補を列挙して吸収する形にしていますが、
  実際のレスポンスで名称が異なる場合は調整が必要です。生のレスポンスは`raw_json`列に
  必ず保存されるので、そこから正しいキー名を確認できます。
- Compusophiaのアーカイブファイルの列名も同様に`scripts/archive_csv.py`の
  `COLUMN_ALIASES`で吸収していますが、実ファイルに合わせて調整してください。
- 断面交通量データは主要道路のセンサー設置箇所のみが対象のため、登録地点の近くに
  センサーがない場合はデータが取得できないことがあります(`--radius`を広げて調整)。
- Supabase無料枠はDB容量500MB程度です。5分毎×複数地点を長期間貯めると容量を圧迫する
  可能性があるため、定期的に`get_advisors`等で使用量を確認してください。
