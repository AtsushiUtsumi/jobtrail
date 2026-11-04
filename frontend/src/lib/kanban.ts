import type { ApplicationStatus } from "./labels";

export type DropAction = "apply" | "advance" | "pass" | "close" | "none";

/** カードを列へ落としたときに実行する操作を決める。実際の検証はサーバーが行う。 */
export function planDrop(from: ApplicationStatus, to: ApplicationStatus): DropAction {
  if (from === to || from === "closed") return "none";
  if (to === "closed") return "close";
  if (from === "considering") return to === "applied" ? "apply" : "none";
  if (to === "in_stage") return from === "in_stage" ? "none" : "advance";
  if (from === "in_stage" && (to === "awaiting_next_stage" || to === "offer_pending")) {
    return "pass";
  }
  return "none";
}
