# jobtrail

転職活動（応募企業、選考ステージ、求人票、企業情報、提出書類、スキルシート）を管理するアプリです。
各ユーザーが自分のマシンで起動する **1 インスタンス = 1 ユーザー** の構成で、利用は Claude Desktop からの
MCP 経由が中心です。Web UI は一覧・カンバン・分析・手動編集に使います。

要約・抽出・Excel 記入などの AI 機能はアプリに持たせず、Claude Desktop 側で行います。
アプリはデータの保持とドメインルールの強制に専念します。

## 起動

必要なもの: Docker（Docker Compose v2）

```bash
# Windows
run.bat

# macOS / Linux
./run.sh
```

起動スクリプトは次の順に処理します。

1. Docker が起動しているか確認する
2. `.env` がなければ `.env.example` からコピーする
3. 既存の jobtrail コンテナを削除する（`./data/pg` のデータは残り、他のコンテナにも触れません）
4. ビルドして起動し、healthcheck の完了まで待つ
5. UI と MCP の URL を表示する

### ポートが使用中の場合

既定ではホストの 80 番を使います。他のアプリと競合する場合は `.env` の `HTTP_PORT` を変更して再起動します。

```dotenv
HTTP_PORT=8080
```

## Claude Desktop からの接続

Claude Desktop の設定ファイル（`claude_desktop_config.json`）に次のブロックを追加し、Claude Desktop を再起動します。
`mcp-remote` のために Node.js が必要です。`HTTP_PORT` を変更している場合は URL にポートを付けてください。

```json
{
  "mcpServers": {
    "jobtrail": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost/mcp"]
    }
  }
}
```

Windows では `npx` の実体が `.cmd` なので、`cmd /c` を挟みます。

```json
{
  "mcpServers": {
    "jobtrail": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "mcp-remote", "http://localhost/mcp"]
    }
  }
}
```

設定ファイルの場所は、Claude Desktop の「設定 → 開発者 → 構成を編集」で確認できます。Microsoft Store 版などでは
`%APPDATA%\Claude` ではなく `%LOCALAPPDATA%\Claude-Data\claude_pzs8sxrjxfjjc` にある場合があります。
編集後は、タスクトレイからも Claude Desktop を終了して起動し直してください。

Node.js を使えない場合や HTTP で接続できない場合は、stdio で直接接続できます（jobtrail の起動が前提です）。

```json
{
  "mcpServers": {
    "jobtrail": {
      "command": "docker",
      "args": [
        "compose", "-p", "jobtrail", "exec", "-T", "backend",
        "python", "-m", "jobtrail.adapters.mcp.stdio"
      ]
    }
  }
}
```

検証結果と利用できるツールの一覧は [docs/mcp-tools.md](docs/mcp-tools.md) を参照してください。

## バックアップと復元

`make backup` で `backups/` に SQL ダンプを作成します。

`make` が無い Windows では、**コマンドプロンプト**で次を実行します。

```bat
mkdir backups
docker compose -p jobtrail exec -T db sh -c "pg_dump -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists" > backups\jobtrail.sql
```

復元は jobtrail の起動中に実行します。現在のデータはダンプの内容で置き換えられます。

```bash
# macOS / Linux / Git Bash
docker compose -p jobtrail exec -T db sh -c 'psql -q -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backups/<ファイル名>.sql
```

```bat
rem Windows（コマンドプロンプト）
docker compose -p jobtrail exec -T db sh -c "psql -q -U $POSTGRES_USER -d $POSTGRES_DB" < backups\<ファイル名>.sql
```

## データとプライバシー

- 氏名や職歴などの個人情報を扱います。データは `./data/pg` に保存され、各ユーザーのマシンに閉じています。
- MCP で Claude に渡した内容は、Claude の利用の一環として Anthropic に送信されます。何を渡すかは
  Claude への指示で制御してください。スキルシートの `disclosure` は社外提出物に使う際の目印です。
- 認証はありません。`127.0.0.1` にのみ公開し、`Host` ヘッダーと（`/mcp` では）`Origin` ヘッダーを
  localhost に限定して DNS rebinding を防いでいます。**LAN やインターネットに公開しないでください。**

## 開発

| コマンド | 内容 |
|---|---|
| `make up` / `make down` | 起動 / 停止 |
| `make test` | テスト用 PostgreSQL を立ててバックエンドのテストを実行 |
| `make lint` | ruff、mypy、import-linter、フロントの lint / 型 / テスト |
| `make migrate` | マイグレーションを適用 |
| `make backup` | `pg_dump` でバックアップ |
| `make openapi` | OpenAPI を書き出し、フロントの型を再生成 |

`make` が無い環境でのテスト実行:

```bash
docker compose -p jobtrail-test -f docker-compose.test.yml run --rm --build test
docker compose -p jobtrail-test -f docker-compose.test.yml down -v
```

新しい操作は `backend/src/jobtrail/usecase/registry.py` に 1 行登録すると、REST ルートと MCP ツールの両方が
生成されます。設計は [docs/domain-model.md](docs/domain-model.md)、[docs/usecases.md](docs/usecases.md)、
[docs/adr/](docs/adr/) を参照してください。
