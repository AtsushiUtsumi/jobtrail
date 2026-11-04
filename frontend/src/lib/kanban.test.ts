import { describe, expect, it } from "vitest";
import { planDrop } from "./kanban";
import { closableOutcomes, statusLabel } from "./labels";

describe("planDrop", () => {
  it("検討中から応募済みへの移動は応募になる", () => {
    expect(planDrop("considering", "applied")).toBe("apply");
  });

  it("検討中から選考中へは直接移動できない", () => {
    expect(planDrop("considering", "in_stage")).toBe("none");
  });

  it("応募済み・次ステージ待ち・内定から選考中への移動はステージ追加になる", () => {
    expect(planDrop("applied", "in_stage")).toBe("advance");
    expect(planDrop("awaiting_next_stage", "in_stage")).toBe("advance");
    expect(planDrop("offer_pending", "in_stage")).toBe("advance");
  });

  it("選考中から次の列への移動は通過の記録になる", () => {
    expect(planDrop("in_stage", "awaiting_next_stage")).toBe("pass");
    expect(planDrop("in_stage", "offer_pending")).toBe("pass");
  });

  it("進行中の応募はどの列からでも終了にできる", () => {
    expect(planDrop("considering", "closed")).toBe("close");
    expect(planDrop("in_stage", "closed")).toBe("close");
  });

  it("終了した応募と同じ列への移動は何もしない", () => {
    expect(planDrop("closed", "applied")).toBe("none");
    expect(planDrop("applied", "applied")).toBe("none");
  });
});

describe("closableOutcomes", () => {
  it("検討中は見送りと募集終了のみ", () => {
    expect(closableOutcomes("considering")).toEqual(["passed_over", "posting_closed"]);
  });

  it("応募後は見送りを選べない", () => {
    expect(closableOutcomes("applied")).not.toContain("passed_over");
  });
});

describe("statusLabel", () => {
  it("選考中はステージ種別を含む", () => {
    const label = statusLabel({ status: "in_stage", stage_type: "final", outcome: "in_progress" });
    expect(label).toBe("選考中（最終）");
  });

  it("終了は outcome を表示する", () => {
    expect(statusLabel({ status: "closed", outcome: "rejected" })).toBe("不合格");
  });
});
