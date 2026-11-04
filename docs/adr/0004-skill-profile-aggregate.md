# 0004. SkillProfile を Document とは別の集約にする

**状況**: 書類は Markdown の版の並びだが、スキルシートは企業ごとの様式へ転記する構造化データである。

**決定**: SkillProfile を別集約とし、1 インスタンスに 1 つ持つ。内容は 1 行の JSONB に保存し、
ルートの `version` で楽観ロックする。提出内容は Submission の snapshot に固定する。

**結果**: 要素ごとの更新と条件での絞り込みが容易になる。JSONB なので SQL での集計には向かないが、
MVP の用途では不要である。
