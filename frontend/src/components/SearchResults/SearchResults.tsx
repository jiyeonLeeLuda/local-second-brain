"use client";

import { useState } from "react";
import { SourceCard } from "@/components/SourceCard/SourceCard";
import type { SearchHit } from "@/lib/api/types";
import styles from "./SearchResults.module.css";

interface SearchResultsProps {
  query: string;
  results: SearchHit[];
}

/** LLM 없이 검색 결과(청크)만 나열한다. 새 검색마다 key를 바꿔 펼침 상태를 초기화한다. */
export function SearchResults({ query, results }: SearchResultsProps) {
  const [expanded, setExpanded] = useState<ReadonlySet<number>>(() => new Set());

  function toggle(chunkId: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(chunkId)) next.delete(chunkId);
      else next.add(chunkId);
      return next;
    });
  }

  return (
    <section className={styles.panel} aria-labelledby="search-heading">
      <h2 id="search-heading" className={styles.label}>
        검색 결과 {results.length}개
      </h2>
      <p className={styles.query}>{query}</p>

      {results.length === 0 ? (
        <p className={styles.empty}>일치하는 노트 조각이 없습니다. 인덱싱이 되어 있는지 확인해 주세요.</p>
      ) : (
        <ol className={styles.list}>
          {results.map((hit, i) => (
            <li key={hit.chunk_id}>
              <SourceCard
                n={i + 1}
                hit={hit}
                expanded={expanded.has(hit.chunk_id)}
                onToggle={() => toggle(hit.chunk_id)}
              />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
