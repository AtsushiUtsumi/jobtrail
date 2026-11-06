# jobtrail 仕様書（実装依頼用）

転職活動管理 WEB アプリ **jobtrail** の仕様。Claude Code はこの文書を実装の唯一の起点として扱うこと。
「【確定】」は合意済み、「【暫定】」は設計者の推奨で進める項目（実装中に問題があれば報告して変更可）、「【要検証】」は実機確認が必要な項目。

---

## 1. 概要

- 転職活動（応募企業、選考ステージ、求人票、企業情報、提出書類、スキルシート）を管理するアプリ。
- 各ユーザーが自分のマシンで `docker compose` により起動する。**1 インスタンス = 1 ユーザー**。将来、他人にも配布する。
- 利用は **Claude Desktop から MCP 経由**が中心。Web UI は一覧・カンバン・分析・手動編集用。
- **原則：UI でできることは MCP でもできる**。REST と MCP は同一のユースケース層を呼ぶ薄いアダプタとする。
- AI 機能（要約・抽出・Excel 記入など）は**アプリに持たせない**。Claude Desktop 側が行い、アプリはデータの保持とドメインルールの強制に専念する。
- アプリ名・パッケージ名・MCP サーバー名：`jobtrail`。

## 2. 設計原則

1. ユースケース層が唯一の入口。ドメインロジックや整合性チェックをアダプタ（REST/MCP）に置かない。
2. ユースケースは 1 か所（`usecase/registry.py`）で登録し、REST ルートと MCP ツールの**両方をそこから生成**する。片方だけ作れない構造にする。
3. 入出力スキーマ（Pydantic v2）は REST/MCP で共有する。
4. MCP ツールは**意図（ユースケース）単位**。画面の部品単位や CRUD 単位で増やさない。
5. Claude は画面をクリックできないので、**対象を名前から特定する検索系ツール**を必ず用意する。
6. 破壊的操作は論理削除＋復元。物理削除のツールは作らない。
7. エラーは「コード・原因・次の一手のヒント」を持つ構造化エラーで返す（UI は表示、Claude は自力で修正して再試行できる）。
8. 集約をまたぐ参照は ID のみ（オブジェクト参照しない）。
9. 依存の向き：`adapters → usecase → domain`、`infra → domain`。`domain` は外部ライブラリに依存しない（import-linter で CI 検証）。

## 3. 技術スタック【確定】

### バックエンド
- Python 3.12+、パッケージ管理 uv
- FastAPI（1 プロセスで `/api` と `/mcp` を公開）
- MCP：公式 Python SDK（`mcp`）、Streamable HTTP。registry から**自前で**ツールを生成する（OpenAPI→MCP の自動変換ツールは使わない）
- Pydantic v2
- SQLAlchemy 2.x（**imperative mapping**：domain を ORM に依存させない）、Alembic
- Lint/Format：ruff、型：mypy（strict）、テスト：pytest、依存方向：import-linter

### フロントエンド
- Vite + React + TypeScript
- TanStack Query（ポーリングによる自動更新）
- openapi-typescript + openapi-fetch（REST の型を OpenAPI から自動生成）
- React Router、Tailwind CSS + shadcn/ui、dnd-kit（カンバン）
- ESLint + Prettier、Vitest

### DB【確定】
- **PostgreSQL 17**
- 日時は全て `timestamptz`、可変構造は `JSONB`、主キーは UUID
- MVP では `pg_trgm` / `pgvector` / `LISTEN/NOTIFY` は使わない（後回し）

### 入れないもの
認証（JWT/OAuth 等）、LLM SDK（Anthropic SDK 等）、Celery/Redis/MQ、SSR（Next.js 等）、Excel 処理ライブラリ、アプリ側の Web 取得/スクレイピング。

## 4. 実行環境・配布【確定】

### docker compose（プロジェクト名 `jobtrail`）

| サービス | 内容 | 公開 |
|---|---|---|
| `db` | `postgres:17`。データは `./data/pg` にバインドマウント。healthcheck は `pg_isready` | `expose: 5432`（ホストに出さない） |
| `backend` | FastAPI。起動時に `alembic upgrade head` を実行。healthcheck は `GET /api/health` | `expose: 8000`（ホストに出さない） |
| `frontend` | nginx。ビルド済み React 静的ファイルを配信し、`/api` と `/mcp` を `backend` にリバースプロキシ | `127.0.0.1:${HTTP_PORT:-80}:80` |

- `backend` は `db` が healthy になってから、`frontend` は `backend` が healthy になってから起動（`depends_on: condition: service_healthy`）。
- **外部に出すのは frontend の 80 番のみ**。`127.0.0.1` バインドを必須とする（LAN に公開しない）。
- `HTTP_PORT` は `.env` で変更可（ポート競合対策）。`.env.example` に `HTTP_PORT=80` ほか DB 接続情報・本文サイズ上限等を記載。
- UI・API・MCP が同一オリジンになるため CORS 設定は不要。

### nginx 設定の要点
- `/`：静的ファイル（`try_files $uri /index.html`）
- `/api/`：`proxy_pass http://backend:8000`
- `/mcp`：`proxy_pass http://backend:8000`、`proxy_http_version 1.1`、**`proxy_buffering off`**、`proxy_read_timeout 3600s`（ストリーミング応答のため必須）

### 起動スクリプト `run.bat` / `run.sh`（リポジトリ直下）
起動は必ずこれらで行う。処理順：
1. Docker が起動しているか確認（`docker info`）。失敗ならエラー終了
2. `.env` がなければ `.env.example` からコピー
3. **既存の jobtrail コンテナを全て削除**：`docker compose -p jobtrail down --remove-orphans`（`-v` は付けない。`./data/pg` のデータは残る。マシン上の他のコンテナは消さない）
4. `docker compose -p jobtrail up -d --build --wait`（healthcheck 完了まで待機）
5. UI と MCP の URL を表示（`HTTP_PORT` が 80 以外ならポート付き）

※ `run.sh` / `run.bat` は作成済みの別ファイルを使う。`.gitattributes` に `*.sh text eol=lf`、`*.bat text eol=crlf` を入れ、`run.sh` に実行権限を付ける。

### バックアップ
`make backup`（`pg_dump`）を用意し、README に復元手順を書く。

### Claude Desktop からの接続【要検証】
- エンドポイント：`http://localhost/mcp`（`HTTP_PORT` 変更時はポート付き）
- ユーザーが設定ファイルに貼る 1 ブロックのキーは `jobtrail`。候補（要実機検証）：
  ```json
  { "mcpServers": { "jobtrail": { "command": "npx", "args": ["-y", "mcp-remote", "http://localhost/mcp"] } } }
  ```
  `http` 接続で拒否される場合は `--allow-http` 等のオプションを検討する。
- フォールバックとして **stdio エントリポイント**（`adapters/mcp/stdio.py`）も用意する。同じ registry から同じツールを公開し、`docker compose -p jobtrail exec -T backend python -m jobtrail.adapters.mcp.stdio` で起動できること。
- どの方式で動いたかを README と `docs/mcp-tools.md` に記録する。

## 5. ディレクトリ構成

```
jobtrail/
├── docker-compose.yml
├── .env.example
├── run.sh / run.bat
├── Makefile                 # up / down / test / migrate / backup
├── README.md                # 起動手順、Claude Desktop 接続設定、バックアップ/復元
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── migrations/
│   ├── src/jobtrail/
│   │   ├── main.py          # FastAPI 起動。/api と /mcp をマウント
│   │   ├── config.py        # 本文サイズ上限、ページング上限、鮮度日数など
│   │   ├── domain/          # 外部ライブラリ非依存
│   │   │   ├── shared/      # errors.py, value_objects.py, ids.py
│   │   │   ├── company/     # company.py, company_source.py, repository.py
│   │   │   ├── application/ # application.py, stage.py, job_posting.py, value_objects.py, repository.py
│   │   │   ├── document/    # document.py, repository.py
│   │   │   └── skill_profile/ # skill_profile.py, submission.py, repository.py
│   │   ├── usecase/         # REST/MCP 共有の唯一の入口
│   │   │   ├── registry.py
│   │   │   ├── company/  application/  document/  skill_profile/
│   │   │   └── query/       # pipeline.py, stats.py, next_actions.py（読み取り専用）
│   │   ├── schemas/         # Pydantic 入出力（REST/MCP 共有）
│   │   ├── infra/
│   │   │   ├── db/          # session.py, models.py, repositories/
│   │   │   └── unit_of_work.py   # トランザクション境界、楽観ロック
│   │   └── adapters/
│   │       ├── rest/        # router.py（registry から生成）, error_handlers.py
│   │       └── mcp/         # server.py（registry から生成）, descriptions.py, stdio.py
│   └── tests/               # domain / usecase / adapters(test_parity.py) / integration
├── frontend/                # Dockerfile, nginx.conf, vite, src/{api,pages,components,hooks}
├── data/                    # .gitkeep（data/pg は .gitignore）
└── docs/                    # domain-model.md, usecases.md, mcp-tools.md, adr/
```

## 6. ドメインモデル

### 6.1 集約一覧【確定】

| 集約 | ルート | 内容 |
|---|---|---|
| Company | Company | 企業の基本情報 |
| CompanySource | CompanySource | 企業情報の保存ページ 1 件（本文が大きいので別集約） |
| Application | Application | 応募。Stage を内包 |
| JobPostingSnapshot | JobPostingSnapshot | 求人票の版（追記のみ） |
| Document | Document | 職務経歴書・履歴書など。DocumentVersion の並び |
| SkillProfile | SkillProfile | スキルシートのマスタ（構造化データ）。**Document とは別集約**【暫定】 |
| Submission | Submission | スキルシート等の提出記録（応募 × 日付 × 内容スナップショット） |

**InterviewLog は MVP では実装しない**【確定】。ドメイン・ユースケース・UI・MCP ツールから外す。面接で聞かれたことは Stage の `memo` に書く運用。Stage は ID を持つエンティティのままにし、後から `ApplicationId + StageId` 参照で追加できるようにしておく。

### 6.2 Company
- 属性：`id, name, url, memo, created_at, updated_at, deleted_at, version`
- 不変条件：同一の社名（正規化後）または同一 URL の重複登録を防ぐ。論理削除と復元が可能。

### 6.3 CompanySource
- 属性：`id, company_id, source_type, url, fetched_at, content_hash, raw_text, summary, extracted_fields(JSONB), acquired_by, revision`
- `source_type`：採用ページ / 会社概要 / ブログ / ニュース / 口コミ / その他。**口コミ・評判系は主観的情報として type で区別し、要約に混ぜない**。
- `acquired_by`：`claude_fetch` / `user_paste`
- 同一 URL の再保存：`content_hash` が同じなら変更なし（`fetched_at` のみ更新して `unchanged` を返す）、異なれば新しい版（`revision` + 1）として追記。過去の版は不変。
- `raw_text` はサイズ上限あり（`config.py`、既定 50,000 文字）。超過時は「分割して保存する」ヒント付きエラー。
- `raw_text`（事実）と `summary`（解釈）は別フィールド。
- `extracted_fields`【暫定】：主要項目（`employee_count, founded_year, tech_stack[], remote_policy`）を固定キー、それ以外は自由 JSON（`extra`）。

### 6.4 Application（状態機械の中核）
- 属性：`id, company_id, position(職種), channel, agent_name, priority(志望度。100 点満点の整数、既定は 50), applied_at, outcome, stages[], submitted_document_version_id, memo, created_at, updated_at, version`
- `ApplicationChannel`：直接応募 / エージェント / スカウト / リファラル
- `outcome`：進行中 / 内定承諾 / 内定辞退 / 落選 / 応募辞退 / 募集終了 / **見送り**（応募前に見送り）
- **初期状態は「検討中」**【確定】：`stages` が空かつ `applied_at` が空。求人を保存しただけの段階も Application として扱う。`apply(applied_at)` で「書類選考」へ遷移。
- **status は保存せず導出する**：
  - ステージは 検討中 / カジュアル面談 / 書類選考 / 一次面接 / 二次面接 / 内定 / 落選 / 内定承諾 / 内定辞退 / 応募辞退 の 10 種。カンバンの列もこの順に並ぶ
  - `outcome` が落選・内定承諾・内定辞退・応募辞退 → その値
  - `outcome` が見送り・募集終了 → 終了（カンバンには出さず、一覧で確認する）
  - `applied_at` が空 → 検討中
  - `stages` が空 → 書類選考
  - それ以外 → 最後の Stage の種別（結果待ちでも通過でも同じ）
- 不変条件：
  - 検討中の間は Stage を追加できない
  - 結果未確定の Stage があるとき、次の Stage を追加できない
  - 不合格・辞退の Stage の後ろに Stage を追加できない
  - 終了状態では Stage の追加・変更ができない（再開は明示的な `reopen`）
  - 見送りは検討中からのみ可能
  - Stage の結果を「不合格」「辞退」で記録したら outcome を自動で「不合格」「応募辞退」にする【暫定】
- メソッド：`apply`, `add_stage`, `record_stage_result`, `reschedule_stage`, `close(outcome)`, `reopen`, `update_details`（部分更新）, `attach_submitted_document(version_id)`
- 楽観ロック：`version`。更新は `WHERE version = :expected`。不一致は `ConflictError`（HTTP 409）。UI は `expected_version` 必須、MCP は任意（指定時のみ検証）【暫定】。

### 6.4.1 Stage（Application 内のエンティティ）
- 属性：`id, type, label(任意の表示名), scheduled_at, result, memo`
- `StageType`：カジュアル面談 / 書類選考 / 一次面接 / 二次面接 / 内定
- `StageResult`：結果待ち / 通過 / 不合格 / 辞退
- **Stage の順序は自由**（種別の並びを検証しない。追加順）【暫定】

### 6.5 JobPostingSnapshot
- 属性：`id, application_id, url, fetched_at, content_hash, raw_text, summary, salary_range(下限/上限/通貨/期間), location, employment_type, remote_policy, tech_stack[], required[], preferred[], extra(JSONB), acquired_by, revision`
- 追記のみ。過去の版は不変。同一 `content_hash` なら新版を作らない。
- 1 応募に複数の版を持てる。変更検知は `content_hash` の比較。

### 6.6 Document / DocumentVersion
- Document：`id, name, kind(職務経歴書/履歴書/その他), versions[]`。DocumentVersion：`id, document_id, number, body(Markdown), created_at, note`
- 版は追記のみ。**Application に紐づけられた（提出済み）版は編集不可**。
- 本文は Markdown のテキストのみ（PDF 等のファイル添付は MVP 外）。

### 6.7 SkillProfile（スキルシートのマスタ）
- 1 インスタンスに 1 つ。構造化データを部分更新できる。
- 構成：
  - `basic`：氏名、生年月日（または年齢）、最寄り、希望条件、自己 PR、強み要約
  - `careers[]`：会社名、在籍期間、雇用形態、役割、概要
  - `projects[]`：期間、案件概要、役割、規模（人数）、使用技術（言語・FW・DB・インフラ）、担当工程、成果、**`disclosure`（公開可否）、`anonymized_name`（匿名化後の表記）**
  - `skills[]`：技術名、カテゴリ、経験年数、習熟度
  - `qualifications[]`：資格名、取得日
- 各要素は ID を持ち、個別の追加・更新・削除ができる。ルートに `version`（楽観ロック）。
- 取得系：全体を JSON で返す、条件で絞り込んで返す（例：技術名で絞ったプロジェクト、直近 N 年）。
- 初期登録の手間を減らすため、既存のスキルシートを Claude に読ませて一括投入できる `import_skill_profile`（入力は構造化 JSON）を用意する【暫定】。

### 6.8 Submission
- 属性：`id, application_id, submitted_at, kind, template_file_name(企業から受け取った様式のファイル名), received_at, snapshot(JSONB: 提出時点の SkillProfile の内容), document_version_id(任意), memo`
- **Excel ファイル本体はアプリで保持しない**【暫定】。Excel の読み取り・転記・出力は Claude 側が行い、アプリは SkillProfile の保持と「いつ・どの応募に・どの内容を提出したか」の記録のみ行う。

## 7. ユースケース／MCP ツール一覧

凡例：★=MVP。全てユースケース層に実装し、REST と MCP の両方に公開する。一覧系は絞り込み・ソート・`limit`（既定 50・上限 200）・`offset` をパラメータ化し、総件数を返す。

### 企業
- ★ `register_company`, `update_company`, `delete_company`（論理）, `restore_company`
- ★ `find_companies`（社名・状態で検索。**ID 解決用**）, `get_company`
- ★ `save_company_source`, `get_company_sources`, `get_company_source`（本文つき）, `update_company_source_summary`（再要約）, `find_stale_company_sources`（取得から一定日数経過）

### 応募
- ★ `add_application`（企業＋職種＋経路。企業が未登録なら同時作成。**まず `find_companies` で検索させ、見つからなければ作成するようツール説明文で誘導**）
- ★ `update_application`（部分更新）, `apply`, `close_application`, `reopen_application`
- ★ `find_applications`（ステータス（複数可）・企業・経路・期間・志望度。既定は更新順で `sort` で志望度順に変更可）, `get_application`（Stage・求人票・提出情報を含む）
- ★ `advance_stage`（Stage 追加）, `record_stage_result`, `reschedule_stage`, `update_stage_memo`
- ★ `save_job_posting`, `get_job_postings`, `get_job_posting`（本文つき）, `update_job_posting_summary`

### 書類
- ★ `create_document`, `add_document_version`, `get_document`, `list_documents`, `attach_document_to_application`（提出した版の紐づけ）

### スキルシート
- ★ `get_skill_profile`（全体 or 絞り込み）, `update_skill_profile_basic`
- ★ `add_career` / `update_career` / `remove_career`、`add_project` / `update_project` / `remove_project`、`add_skill` / `update_skill` / `remove_skill`、`add_qualification` / `update_qualification` / `remove_qualification`
- ★ `import_skill_profile`
- ★ `record_submission`, `list_submissions`, `get_submission`

### 分析（読み取り専用・集約を経由せず直接クエリ）
- ★ `get_pipeline`：ステータス別の応募一覧（カンバン用）。既定は更新順で `sort` で志望度順に変更可
- ★ `get_stats`：ステージ別通過率、応募から内定までの日数、経路別比較。**分母は応募済み以降のみ（検討中・見送りは除外）**
- ★ `get_next_actions`：近日（既定 7 日以内）の予定、結果待ちが長い応募（既定 7 日超）、古い企業情報（既定 90 日超）、提出書類が未紐づけの応募。閾値は `config.py`
- ☆ 企業間の比較表（抽出フィールドの並列表示）、書類の版間差分

## 8. エラー設計
- ドメイン例外は `code`（機械可読）、`message`（原因）、`hint`（次の一手）を持つ。
- 例：`STAGE_PENDING_RESULT`（hint：「直前の Stage の結果を `record_stage_result` で記録してください」）、`APPLICATION_CLOSED`、`NOT_APPLIED_YET`、`DUPLICATE_COMPANY`（既存の ID を返す）、`CONFLICT`（現在の version を返す）、`CONTENT_TOO_LARGE`、`NOT_FOUND`。
- REST：HTTP ステータス（404/409/422 等）＋同じ JSON ボディ。MCP：`isError` 付きで同じ JSON を返す。

## 9. セキュリティ【確定】
- 認証なし。**localhost 限定が前提**（`127.0.0.1` バインド）。
- DNS rebinding 対策：`Host` ヘッダーを `localhost` / `127.0.0.1` に限定し、`/mcp` では `Origin` ヘッダーも検証する。
- `db` と `backend` はホストにポートを公開しない。
- 個人情報（氏名・職歴等）を扱う。データは各ユーザーのローカルに閉じることを README に明記し、MCP 経由で Claude に渡ることも説明する。

## 10. Web UI【確定】
閲覧中心＋手動編集。MCP でできることは UI でもできるが、UI は画面単位の少数に留める。
- ダッシュボード（パイプライン、次にやること）
- 応募一覧／カンバン（dnd-kit でステージ移動）、応募詳細（Stage 履歴、求人票、提出書類、提出記録）
- 企業一覧／詳細（保存済みソース、関連する応募）
- 書類管理
- スキルシート編集・提出記録
- 貼り付け入力フォーム（URL＋本文の貼り付けで `save_company_source` / `save_job_posting` を呼ぶ。Claude の取得が使えない場合の代替経路）
- TanStack Query のポーリング（既定 10 秒）で自動更新。409 受信時は再取得して通知。

## 11. テスト・CI
- `domain/`：DB なしの単体テスト。**Application の不変条件・状態導出を網羅**する（正常系・全ての違反ケース）。
- `usecase/`：ユースケース単位のテスト（インメモリ Repository 可）。
- `integration/`：実 PostgreSQL を使った結合テスト（楽観ロック、重複防止、版管理を含む）。
- `adapters/test_parity.py`：registry の全ユースケースが REST と MCP の両方に存在することを検証する。
- import-linter：`domain` が他層に依存しないこと、`usecase` が `adapters`/`infra` に依存しないことを検証。
- GitHub Actions：ruff、mypy、pytest、フロントの lint/型/テスト、compose の起動確認。

## 12. スコープ外（MVP では作らない）
ユーザー管理・認証・マルチテナント、アプリ内の LLM 呼び出し、アプリ側の Web 取得/スクレイピング、InterviewLog、転職エージェントの独立管理、カレンダー・メール連携・通知、手動 TODO（Task）、Excel/PDF ファイル本体の保管、`LISTEN/NOTIFY` による即時更新、全文検索・ベクトル検索。

## 13. 実装の進め方（推奨順）
1. **雛形**：compose（db/backend/frontend）、`run.sh`/`run.bat`、`/api/health`、nginx 設定、CI、import-linter。
2. **Application 集約**（`domain/application/`）：状態導出・不変条件・テスト。ここを最優先で固める。
3. Company / CompanySource / JobPostingSnapshot の domain とテスト。
4. infra：SQLAlchemy imperative mapping、Alembic、Unit of Work、楽観ロック、結合テスト。
5. usecase 層と `registry.py`、REST・MCP アダプタ、`test_parity.py`、stdio エントリポイント。
6. Document / SkillProfile / Submission。
7. 分析クエリ（`get_pipeline` / `get_stats` / `get_next_actions`）。
8. フロントエンド（OpenAPI から型生成 → 各画面）。
9. README、`docs/`（ドメインモデル、ユースケース、MCP ツール、ADR）。Claude Desktop 接続の実機検証結果を記録。

ADR に記録する判断：PostgreSQL 採用、REST/MCP のユースケース共有、InterviewLog の保留、SkillProfile の別集約化、AI 機能を Claude 側に置く方針、Excel 処理をアプリに持たせない方針、80 番ポートと localhost 限定。

## 14. 未確定・要確認の項目
- **【要検証】Claude Desktop からの HTTP MCP 接続方式**（§4）。最初に PoC（ヘルスチェック用の `ping` ツール 1 本）で確認し、結果に応じて接続方式を README に確定する。
- 【暫定】Stage 順序の自由化、抽出フィールドの「主要項目固定＋自由 JSON」、SkillProfile の別集約化、不合格結果での outcome 自動設定、MCP での `expected_version` 任意化。変更が必要なら実装前に報告すること。
- アプリ名の衝突確認（GitHub / PyPI / npm）は未実施。公開前に行う。
