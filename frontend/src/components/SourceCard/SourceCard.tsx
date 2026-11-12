"use client";

import { useId } from "react";
import type { SearchHit } from "@/lib/api/types";
import { basename, dirname, formatScore } from "@/lib/format";
import styles from "./SourceCard.module.css";

/** 접힌 상태에서 보여줄 발췌 길이 */
const PREVIEW_CHARS = 180;

interface SourceCardProps {
  hit: SearchHit;
  /** 답변 출처일 때의 번호. 검색 결과에서는 생략 */
  n?: number;
  /** DOM id. 인용 [n] 클릭 시 스크롤 대상 */
  id?: string;
  expanded: boolean;
  onToggle: () => void;
  active?: boolean;
  /** 답변 본문에서 인용되지 않은 출처 */
  uncited?: boolean;
}

export function SourceCard({ hit, n, id, expanded, onToggle, active = false, uncited = false }: SourceCardProps) {
  const bodyId = useId();
  const needsToggle = hit.text.length > PREVIEW_CHARS;
  const shown = expanded || !needsToggle ? hit.text : `${hit.text.slice(0, PREVIEW_CHARS).trimEnd()}…`;
  const dir = dirname(hit.file_path);

  return (
    <article
      id={id}
      tabIndex={-1}
      className={styles.card}
      data-active={active || undefined}
      data-uncited={uncited || undefined}
      aria-current={active || undefined}
    >
      <header className={styles.header}>
        {n !== undefined && <span className={styles.badge}>{n}</span>}
        <div className={styles.meta}>
          <p className={styles.file} title={hit.file_path}>
            {basename(hit.file_path)}
            {dir && <span className={styles.dir}>{dir}</span>}
          </p>
          {hit.heading_path && <p className={styles.heading}>{hit.heading_path}</p>}
        </div>
        <span className={styles.score} title="검색 점수">
          {formatScore(hit.score)}
        </span>
      </header>

      <p id={bodyId} className={styles.text}>
        {shown}
      </p>

      <footer className={styles.footer}>
        {uncited && <span className={styles.note}>본문에서 인용되지 않음</span>}
        {needsToggle && (
          <button type="button" className={styles.toggle} onClick={onToggle} aria-expanded={expanded} aria-controls={bodyId}>
            {expanded ? "접기" : "전체 보기"}
          </button>
        )}
      </footer>
    </article>
  );
}
