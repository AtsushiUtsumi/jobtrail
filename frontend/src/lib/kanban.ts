import type { ApplicationStatus, Outcome, StageType } from "./labels";

export type DropAction = "apply" | "advance" | "close" | "none";

const STAGE_COLUMNS: ApplicationStatus[] = [
  "casual",
  "document",
  "first_interview",
  "second_interview",
  "offer",
];
const CLOSE_COLUMNS: ApplicationStatus[] = [
  "rejected",
  "offer_accepted",
  "offer_declined",
  "withdrawn",
];

/** カードを列へ落としたときに実行する操作を決める。実際の検証はサーバーが行う。 */
export function planDrop(from: ApplicationStatus, to: ApplicationStatus): DropAction {
  if (from === to || from === "closed" || CLOSE_COLUMNS.includes(from)) return "none";
  if (CLOSE_COLUMNS.includes(to)) return from === "considering" ? "none" : "close";
  if (from === "considering") return to === "document" ? "apply" : "none";
  const moved = STAGE_COLUMNS.indexOf(to) - STAGE_COLUMNS.indexOf(from);
  return STAGE_COLUMNS.includes(to) && moved > 0 ? "advance" : "none";
}

/** 列の status はステージ種別・終了理由と同じ値を使う。 */
export const stageTypeOf = (column: ApplicationStatus) => column as StageType;
export const outcomeOf = (column: ApplicationStatus) => column as Outcome;
