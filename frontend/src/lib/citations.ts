/**
 * LLM 답변 본문에서 [1], [2], [1, 3], [1-2] 같은 인용 표기를 찾아
 * 텍스트 조각과 인용 조각으로 나눈다. 렌더링 쪽에서 인용 조각을 버튼으로 바꾼다.
 */

export type AnswerSegment =
  | { type: "text"; text: string }
  | { type: "citation"; raw: string; numbers: number[] };

// 대괄호 안에 숫자, 쉼표, 공백, 하이픈(범위)만 있는 경우만 인용으로 본다.
const CITATION_RE = /\[(\d+(?:\s*[-–,]\s*\d+)*)\]/g;

/** 범위 표기가 비정상적으로 넓을 때(예: [1-9999]) 펼치지 않는 상한 */
const MAX_RANGE = 50;

function expand(inner: string): number[] | null {
  const numbers: number[] = [];
  for (const part of inner.split(",")) {
    const range = part.split(/[-–]/).map((s) => Number.parseInt(s.trim(), 10));
    if (range.length === 1) {
      numbers.push(range[0]);
    } else if (range.length === 2) {
      const [start, end] = range;
      if (end < start || end - start > MAX_RANGE) return null;
      for (let i = start; i <= end; i++) numbers.push(i);
    } else {
      return null;
    }
  }
  return [...new Set(numbers)];
}

export function parseCitations(answer: string): AnswerSegment[] {
  const segments: AnswerSegment[] = [];
  let last = 0;

  for (const match of answer.matchAll(CITATION_RE)) {
    const numbers = expand(match[1]);
    if (!numbers) continue;

    const start = match.index;
    if (start > last) segments.push({ type: "text", text: answer.slice(last, start) });
    segments.push({ type: "citation", raw: match[0], numbers });
    last = start + match[0].length;
  }

  if (last < answer.length) segments.push({ type: "text", text: answer.slice(last) });
  return segments;
}

/** 답변 본문에서 실제로 인용된 출처 번호 집합 */
export function citedNumbers(segments: AnswerSegment[]): Set<number> {
  const cited = new Set<number>();
  for (const seg of segments) {
    if (seg.type === "citation") seg.numbers.forEach((n) => cited.add(n));
  }
  return cited;
}
