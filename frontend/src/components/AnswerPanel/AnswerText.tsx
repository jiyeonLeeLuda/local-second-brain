"use client";

import { Fragment, useMemo } from "react";
import { parseCitations } from "@/lib/citations";
import styles from "./AnswerPanel.module.css";

interface AnswerTextProps {
  answer: string;
  /** 출처 목록에 실제로 존재하는 번호 */
  available: ReadonlySet<number>;
  activeSource: number | null;
  onCite: (n: number) => void;
}

/** 답변 본문을 렌더링하면서 [n] 인용 표기를 출처 카드로 이동하는 버튼으로 바꾼다. */
export function AnswerText({ answer, available, activeSource, onCite }: AnswerTextProps) {
  const segments = useMemo(() => parseCitations(answer), [answer]);

  return (
    <div className={styles.answer}>
      {segments.map((seg, i) => {
        if (seg.type === "text") return <Fragment key={i}>{seg.text}</Fragment>;

        // 출처 목록에 없는 번호가 하나라도 있으면 원문 그대로 둔다 (LLM이 번호를 지어낸 경우).
        if (!seg.numbers.every((n) => available.has(n))) {
          return (
            <span key={i} className={styles.citeMissing} title="출처 목록에 없는 번호입니다">
              {seg.raw}
            </span>
          );
        }

        return (
          <span key={i} className={styles.citeGroup}>
            {seg.numbers.map((n) => (
              <button
                key={n}
                type="button"
                className={styles.cite}
                data-active={activeSource === n || undefined}
                onClick={() => onCite(n)}
                aria-label={`출처 ${n}번 보기`}
              >
                {n}
              </button>
            ))}
          </span>
        );
      })}
    </div>
  );
}
