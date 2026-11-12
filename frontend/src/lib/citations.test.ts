import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { citedNumbers, parseCitations } from "./citations.ts";

describe("parseCitations", () => {
  it("인용이 없으면 텍스트 조각 하나를 반환한다", () => {
    assert.deepEqual(parseCitations("그냥 문장입니다."), [{ type: "text", text: "그냥 문장입니다." }]);
  });

  it("빈 문자열이면 빈 배열", () => {
    assert.deepEqual(parseCitations(""), []);
  });

  it("단일 인용과 연속 인용을 분리한다", () => {
    assert.deepEqual(parseCitations("A는 B다 [1]. C도 그렇다[2][3]"), [
      { type: "text", text: "A는 B다 " },
      { type: "citation", raw: "[1]", numbers: [1] },
      { type: "text", text: ". C도 그렇다" },
      { type: "citation", raw: "[2]", numbers: [2] },
      { type: "citation", raw: "[3]", numbers: [3] },
    ]);
  });

  it("쉼표와 범위 표기를 펼친다", () => {
    const segs = parseCitations("근거 [1, 3] 그리고 [2-4]");
    assert.deepEqual(
      segs.filter((s) => s.type === "citation").map((s) => s.numbers),
      [
        [1, 3],
        [2, 3, 4],
      ],
    );
  });

  it("숫자가 아닌 대괄호는 텍스트로 남긴다", () => {
    assert.deepEqual(parseCitations("배열 [a] 와 [ ] 그리고 [1a]"), [
      { type: "text", text: "배열 [a] 와 [ ] 그리고 [1a]" },
    ]);
  });

  it("역순이거나 너무 넓은 범위는 인용으로 보지 않는다", () => {
    assert.deepEqual(parseCitations("[3-1] [1-999]"), [{ type: "text", text: "[3-1] [1-999]" }]);
  });

  it("citedNumbers는 중복 없이 인용 번호를 모은다", () => {
    assert.deepEqual([...citedNumbers(parseCitations("[2] x [1, 2] y [2]"))].sort(), [1, 2]);
  });
});
