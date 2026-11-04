# MCP ツール

- エンドポイント: `http://localhost/mcp`（`HTTP_PORT` 変更時はポート付き）
- トランスポート: Streamable HTTP（ステートレス、JSON 応答）
- サーバー名: `jobtrail`
- ツール: `usecase/registry.py` の全ユースケース（53 個）。一覧は [usecases.md](usecases.md) を参照

使い方の指針（まず `find_companies` で検索する、など）は `adapters/mcp/descriptions.py` にあり、
ツールの説明文としてクライアントへ渡されます。

## 接続方式の検証結果

検証日: 2026-11-04（Windows 11、Docker Desktop、`HTTP_PORT=8080` および `80`）

| 方式 | 結果 | 確認した内容 |
|---|---|---|
| Streamable HTTP を直接呼び出し（nginx 経由） | 動作 | `tools/list`、`tools/call` |
| `npx -y mcp-remote http://localhost:8080/mcp` | 動作 | `initialize`、`tools/list`（53 個）、`tools/call`（`ping`） |
| `cmd /c npx -y mcp-remote http://localhost/mcp`（シェルを介さず起動） | 動作 | `initialize`、`tools/list`（53 個）、`ping`、`get_pipeline` |
| stdio（`docker compose -p jobtrail exec -T app python -m jobtrail.adapters.mcp.stdio`） | 動作 | `initialize`、`tools/call`（`ping`） |

- `mcp-remote` は `localhost` への `http` 接続を `--allow-http` なしで受け付けました。
- **Claude Desktop アプリ本体からの接続は未検証です。** 上の確認は `mcp-remote` を Claude Desktop と同じ
  stdio の起動方法で動かしたものです。実機で確認したら、この表に結果を追記してください。

## 推奨する接続方式

1. `mcp-remote` 経由（README の設定例）
2. うまくいかない場合は stdio 経由
