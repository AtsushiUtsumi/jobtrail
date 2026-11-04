# ユースケース

ユースケースは `usecase/registry.py` の 1 か所で登録します。REST ルートと MCP ツールは、この登録から生成されます。
入力・出力の型はハンドラーの型注釈から、説明文は docstring から取得します。

## 層の構成

```
adapters (REST / MCP) → usecase → domain
                          ↑
infra ─────────────→ domain     bootstrap.py が infra を usecase へ渡す
```

- `adapters/` はリクエストの変換のみを行い、業務ロジックを持ちません。
- 依存方向は import-linter（`pyproject.toml`）で検証します。
- REST と MCP の差は 1 点だけです。`expected_version` は REST では必須、MCP では任意です。

## 一覧

| 分類 | ユースケース |
|---|---|
| 接続確認 | `ping` |
| 企業 | `register_company` `update_company` `delete_company` `restore_company` `find_companies` `get_company` |
| 企業情報 | `save_company_source` `get_company_sources` `get_company_source` `update_company_source_summary` `find_stale_company_sources` |
| 応募 | `add_application` `update_application` `apply` `close_application` `reopen_application` `find_applications` `get_application` |
| 選考 | `advance_stage` `record_stage_result` `reschedule_stage` `update_stage_memo` |
| 求人票 | `save_job_posting` `get_job_postings` `get_job_posting` `update_job_posting_summary` |
| 書類 | `create_document` `add_document_version` `get_document` `list_documents` `attach_document_to_application` |
| スキルシート | `get_skill_profile` `update_skill_profile_basic` `import_skill_profile` `add_/update_/remove_`（`career` `project` `skill` `qualification`） |
| 提出記録 | `record_submission` `list_submissions` `get_submission` |
| 分析 | `get_pipeline` `get_stats` `get_next_actions` |

一覧系は `limit`（既定 50、上限 200）と `offset` を受け取り、`total` を返します。

## エラー

全ての失敗は同じ形で返ります。

```json
{
  "code": "STAGE_PENDING_RESULT",
  "message": "直前の Stage の結果が未確定です。",
  "hint": "直前の Stage の結果を record_stage_result で記録してください。",
  "details": { "stage_id": "..." }
}
```

| 分類 | REST | MCP |
|---|---|---|
| 見つからない（`NOT_FOUND`） | 404 | `isError: true` |
| 状態の競合・ルール違反（`CONFLICT`、`DUPLICATE_COMPANY` など） | 409 | `isError: true` |
| 本文が上限超過（`CONTENT_TOO_LARGE`） | 413 | `isError: true` |
| 入力不正（`VALIDATION_ERROR`） | 422 | `isError: true` |
