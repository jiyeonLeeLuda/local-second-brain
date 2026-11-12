"use client";

import { useMemo, useState } from "react";
import { SourceCard } from "@/components/SourceCard/SourceCard";
import { citedNumbers, parseCitations } from "@/lib/citations";
import type { AskResponse } from "@/lib/api/types";
import { AnswerText } from "./AnswerText";
import styles from "./AnswerPanel.module.css";

const sourceDomId = (n: number) => `source-${n}`;

interface AnswerPanelProps {
  question: string;
  result: AskResponse;
}

/**
 * 답변 + 출처 카드 목록.
 * 새 답변마다 `key`를 바꿔 마운트하면 펼침/선택 상태가 자연스럽게 초기화된다.
 */
export function AnswerPanel({ question, result }: AnswerPanelProps) {
  const [activeSource, setActiveSource] = useState<number | null>(null);
  const [expanded, setExpanded] = useState<ReadonlySet<number>>(() => new Set());

  const available = useMemo(() => new Set(result.sources.map((s) => s.n)), [result.sources]);
  const cited = useMemo(() => citedNumbers(parseCitations(result.answer)), [result.answer]);

  function toggle(n: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(n)) next.delete(n);
      else next.add(n);
      return next;
    });
  }

  function focusSource(n: number) {
    setActiveSource(n);
    setExpanded((prev) => (prev.has(n) ? prev : new Set(prev).add(n)));
    // 펼쳐진 상태가 그려진 뒤 스크롤한다.
    requestAnimationFrame(() => {
      const el = document.getElementById(sourceDomId(n));
      if (!el) return;
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.focus({ preventScroll: true });
    });
  }

  return (
    <section className={styles.panel} aria-labelledby="answer-heading">
      <h2 id="answer-heading" className={styles.label}>
        답변
      </h2>
      <p className={styles.question}>{question}</p>

      <AnswerText answer={result.answer} available={available} activeSource={activeSource} onCite={focusSource} />

      <h3 className={styles.label}>출처 {result.sources.length}개</h3>
      {result.sources.length === 0 ? (
        <p className={styles.empty}>관련 노트를 찾지 못했습니다.</p>
      ) : (
        <ol className={styles.sources}>
          {result.sources.map((source) => (
            <li key={source.n}>
              <SourceCard
                id={sourceDomId(source.n)}
                n={source.n}
                hit={source}
                expanded={expanded.has(source.n)}
                onToggle={() => toggle(source.n)}
                active={activeSource === source.n}
                uncited={cited.size > 0 && !cited.has(source.n)}
              />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
