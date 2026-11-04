# 0001. PostgreSQL を採用する

**状況**: 1 ユーザー 1 インスタンスの構成で、可変構造（抽出項目、スキルシート、提出時の snapshot）を扱う。

**決定**: PostgreSQL 17 を使い、日時は `timestamptz`、可変構造は `JSONB`、主キーは UUID とする。
`pg_trgm`、`pgvector`、`LISTEN/NOTIFY` は MVP では使わない。

**結果**: SQLite より重いが、配布は docker compose が前提なので利用者の負担は増えない。
部分ユニークインデックスで論理削除と重複防止を両立できる。
