import { describe, expect, it } from "vitest";
import { planDrop } from "./kanban";
import { closableOutcomes, statusLabel } from "./labels";

describe("planDrop", () => {
  it("検討中から書類選考への移動は応募になる", () => {
    expect(planDrop("considering", "document")).toBe("apply");
  });

  it("検討中から他のステージへは直接移動できない", () => {
    expect(planDrop("considering", "first_interview")).toBe("none");
    expect(planDrop("considering", "rejected")).toBe("none");
  });

  it("先のステージへの移動はステージ追加になる", () => {
    expect(planDrop("casual", "document")).toBe("advance");
    expect(planDrop("document", "first_interview")).toBe("advance");
    expect(planDrop("second_interview", "offer")).toBe("advance");
  });

  it("前のステージへは戻せない", () => {
    expect(planDrop("first_interview", "document")).toBe("none");
    expect(planDrop("document", "considering")).toBe("none");
  });

  it("進行中の応募は終了の列へ移動できる", () => {
    expect(planDrop("first_interview", "rejected")).toBe("close");
    expect(planDrop("offer", "offer_accepted")).toBe("close");
    expect(planDrop("offer", "offer_declined")).toBe("close");
    expect(planDrop("document", "withdrawn")).toBe("close");
  });

  it("終了した応募と同じ列への移動は何もしない", () => {
    expect(planDrop("rejected", "document")).toBe("none");
    expect(planDrop("offer_accepted", "offer_declined")).toBe("none");
    expect(planDrop("closed", "document")).toBe("none");
    expect(planDrop("document", "document")).toBe("none");
  });
});

describe("closableOutcomes", () => {
  it("検討中は見送りと募集終了のみ", () => {
    expect(closableOutcomes("considering")).toEqual(["passed_over", "posting_closed"]);
  });

  it("応募後は見送りを選べない", () => {
    expect(closableOutcomes("document")).not.toContain("passed_over");
  });
});

describe("statusLabel", () => {
  it("ステージ名を表示する", () => {
    const label = statusLabel({ status: "second_interview", outcome: "in_progress" });
    expect(label).toBe("二次面接");
  });

  it("通過後は通過を付ける", () => {
    const label = statusLabel({
      status: "first_interview",
      outcome: "in_progress",
      current_stage_result: "passed",
    });
    expect(label).toBe("一次面接（通過）");
  });

  it("落選はステージ名を表示する", () => {
    expect(statusLabel({ status: "rejected", outcome: "rejected" })).toBe("落選");
  });

  it("見送りと募集終了は outcome を表示する", () => {
    expect(statusLabel({ status: "closed", outcome: "passed_over" })).toBe("見送り");
  });
});
