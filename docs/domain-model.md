# ドメインモデル

## 集約

| 集約 | 内容 | 版管理 | 楽観ロック |
|---|---|---|---|
| Company | 企業の基本情報。論理削除と復元が可能 | — | `version` |
| CompanySource | 保存ページの 1 版 | URL ごとに `revision` | — |
| Application | 応募。Stage を内包 | — | `version` |
| JobPostingSnapshot | 求人票の 1 版（追記のみ） | 応募ごとに `revision` | — |
| Document | 書類と DocumentVersion の並び | `number`（追記のみ） | — |
| SkillProfile | スキルシートのマスタ（1 インスタンスに 1 つ） | — | `version` |
| Submission | 提出の記録と、提出時点の内容の snapshot | — | — |

集約をまたぐ参照は ID のみです。`domain/` は標準ライブラリだけに依存します。

## Application の状態

status は保存せず、`derive_status()` が `outcome`・`applied_at`・`stages` から導出します。

| 条件（上から順に判定） | status |
|---|---|
| `outcome` が落選・内定承諾・内定辞退・応募辞退 | `rejected`・`offer_accepted`・`offer_declined`・`withdrawn` |
| `outcome` が見送り・募集終了 | `closed`（理由は `outcome`。カンバンには出さない） |
| `applied_at` が空 | `considering`（検討中） |
| `stages` が空 | `document`（書類選考） |
| 上記以外 | 最後の Stage の種別（`casual`・`document`・`first_interview`・`second_interview`・`offer`） |

### 不変条件

| 違反 | エラーコード |
|---|---|
| 検討中の応募に Stage を追加 | `NOT_APPLIED_YET` |
| 結果未確定の Stage があるのに次を追加 | `STAGE_PENDING_RESULT` |
| 不合格・辞退の Stage の後ろに追加 | `STAGE_TERMINATED` |
| 終了した応募の変更（Stage の追加・結果・日程・メモ、応募、書類の紐づけ） | `APPLICATION_CLOSED` |
| 検討中以外で見送り | `NOT_CONSIDERING` |
| 応募済みへの再度の `apply` | `ALREADY_APPLIED` |
| 終了していない応募の `reopen` | `APPLICATION_NOT_CLOSED` |

Stage の結果を不合格にすると `outcome` は落選に、辞退にすると応募辞退になります。

### 仕様書から補った判断

仕様書に明記がなく、実装時に決めた点です。

- **Stage に `created_at` と `result_recorded_at` を追加**: 仕様の属性だけでは「応募から内定までの日数」と
  「結果待ちが長い応募」を計算できないため。
- **結果を記録・訂正できるのは最新の Stage のみ**（`STAGE_NOT_LATEST`）: 途中に不合格が残ると
  「不合格の後ろに Stage を追加できない」が崩れるため。
- **`reopen` は最後の不合格・辞退の Stage を結果待ちへ戻す**: 戻さないと再開しても次の Stage を追加できないため。
- **検討中から指定できる終了理由は見送りと募集終了のみ**: 応募していないのに不合格や内定にはならないため。
- **`save_job_posting` の同一判定は最新版との比較**: A→B→A と戻った場合は新しい版を作ります。
  `save_company_source` も同様です。
- **終了した応募でも応募情報（職種・メモ等）は編集可能**: 仕様が禁じるのは Stage の変更のみのため。

## 分析の定義

- **分母**: `applied_at` のある応募。検討中と、応募せず見送った応募は含みません。
- **通過率**: 通過 ÷ 結果確定（結果待ちを除く）。
- **内定の時点**: 最初の内定 Stage が追加された時点。無ければ内定承諾・辞退で終了した時点。
- **結果待ちの起点**: 予定日が過ぎていれば予定日、予定日が未定なら Stage の追加日。
