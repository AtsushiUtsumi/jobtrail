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
  casual: "カジュアル面談",
  document: "書類選考",
  first_interview: "一次面接",
  second_interview: "二次面接",
  offer: "内定",
  rejected: "落選",
  offer_accepted: "内定承諾",
  offer_declined: "内定辞退",
  withdrawn: "応募辞退",
  closed: "見送り・募集終了",
};

export const OUTCOME_LABELS: Record<Outcome, string> = {
  in_progress: "進行中",
  offer_accepted: "内定承諾",
  offer_declined: "内定辞退",
  rejected: "落選",
  withdrawn: "応募辞退",
  posting_closed: "募集終了",
  passed_over: "見送り",
};

export const STAGE_TYPE_LABELS: Record<StageType, string> = {
  casual: "カジュアル面談",
  document: "書類選考",
  first_interview: "一次面接",
  second_interview: "二次面接",
  offer: "内定",
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
  outcome: Outcome;
  current_stage_result?: StageResult | null;
}): string {
  if (item.status === "closed") return OUTCOME_LABELS[item.outcome];
  const label = STATUS_LABELS[item.status];
  const passed = item.outcome === "in_progress" && item.current_stage_result === "passed";
  return passed ? `${label}（通過）` : label;
}

/** 終了ダイアログで選べる outcome。ドメインの不変条件に合わせて絞る。 */
export function closableOutcomes(status: ApplicationStatus): Outcome[] {
  if (status === "considering") return ["passed_over", "posting_closed"];
  return ["offer_accepted", "offer_declined", "rejected", "withdrawn", "posting_closed"];
}
