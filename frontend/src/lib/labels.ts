import type { components } from "@/api/schema";

type Schemas = components["schemas"];
export type ApplicationStatus = Schemas["ApplicationStatus"];
export type Outcome = Schemas["Outcome"];
export type StageType = Schemas["StageType"];
export type StageResult = Schemas["StageResult"];
export type ApplicationChannel = Schemas["ApplicationChannel"];
export type SourceType = Schemas["SourceType"];
export type DocumentKind = Schemas["DocumentKind"];
export type SubmissionKind = Schemas["SubmissionKind"];
export type Disclosure = Schemas["Disclosure"];

export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  considering: "検討中",
  applied: "応募済み",
  in_stage: "選考中",
  awaiting_next_stage: "次ステージ待ち",
  offer_pending: "内定（回答待ち）",
  closed: "終了",
};

export const OUTCOME_LABELS: Record<Outcome, string> = {
  in_progress: "進行中",
  offer_accepted: "内定承諾",
  offer_declined: "内定辞退",
  rejected: "不合格",
  withdrawn: "応募辞退",
  posting_closed: "募集終了",
  passed_over: "見送り",
};

export const STAGE_TYPE_LABELS: Record<StageType, string> = {
  document: "書類",
  casual: "カジュアル面談",
  aptitude: "適性検査",
  interview: "面接",
  final: "最終",
  offer: "オファー面談",
};

export const STAGE_RESULT_LABELS: Record<StageResult, string> = {
  pending: "結果待ち",
  passed: "通過",
  rejected: "不合格",
  declined: "辞退",
};

export const CHANNEL_LABELS: Record<ApplicationChannel, string> = {
  direct: "直接応募",
  agent: "エージェント",
  scout: "スカウト",
  referral: "リファラル",
};

export const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  recruit: "採用ページ",
  about: "会社概要",
  blog: "ブログ",
  news: "ニュース",
  review: "口コミ",
  other: "その他",
};

export const DOCUMENT_KIND_LABELS: Record<DocumentKind, string> = {
  career_history: "職務経歴書",
  resume: "履歴書",
  other: "その他",
};

export const SUBMISSION_KIND_LABELS: Record<SubmissionKind, string> = {
  skill_sheet: "スキルシート",
  career_history: "職務経歴書",
  resume: "履歴書",
  other: "その他",
};

export const DISCLOSURE_LABELS: Record<Disclosure, string> = {
  public: "公開可",
  anonymized: "匿名化",
  private: "非公開",
};

export function statusLabel(item: {
  status: ApplicationStatus;
  stage_type?: StageType | null;
  outcome: Outcome;
}): string {
  if (item.status === "closed") return OUTCOME_LABELS[item.outcome];
  if (item.status === "in_stage" && item.stage_type) {
    return `選考中（${STAGE_TYPE_LABELS[item.stage_type]}）`;
  }
  return STATUS_LABELS[item.status];
}

/** 終了ダイアログで選べる outcome。ドメインの不変条件に合わせて絞る。 */
export function closableOutcomes(status: ApplicationStatus): Outcome[] {
  if (status === "considering") return ["passed_over", "posting_closed"];
  return ["offer_accepted", "offer_declined", "rejected", "withdrawn", "posting_closed"];
}
