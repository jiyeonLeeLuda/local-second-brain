"use client";

import { useRef, useState } from "react";
import { AnswerPanel } from "@/components/AnswerPanel/AnswerPanel";
import { ErrorNotice } from "@/components/ErrorNotice/ErrorNotice";
import { ModeTabs, type Mode } from "@/components/ModeTabs/ModeTabs";
import { QuestionForm } from "@/components/QuestionForm/QuestionForm";
import { SearchResults } from "@/components/SearchResults/SearchResults";
import { useElapsedSeconds } from "@/hooks/useElapsedSeconds";
import { useRequest } from "@/hooks/useRequest";
import { api } from "@/lib/api/client";
import type { AskResponse, SearchResponse } from "@/lib/api/types";
import styles from "./StudyWorkspace.module.css";

const TOP_K = 5;

interface Answered {
  id: number;
  question: string;
  result: AskResponse;
}

interface Searched {
  id: number;
  query: string;
  result: SearchResponse;
}

const askFn = (question: string, signal: AbortSignal) => api.ask({ question, k: TOP_K }, signal);
const searchFn = (query: string, signal: AbortSignal) => api.search(query, TOP_K, signal);

export function StudyWorkspace() {
  const [mode, setMode] = useState<Mode>("ask");
  const ask = useRequest(askFn);
  const search = useRequest(searchFn);
  const seqRef = useRef(0);

  // 마지막으로 성공한 결과. 요청 상태와 분리해 두면 로딩/에러 중에도 이전 결과를 보여줄 수 있다.
  const [answered, setAnswered] = useState<Answered | null>(null);
  const [searched, setSearched] = useState<Searched | null>(null);

  const current = mode === "ask" ? ask : search;
  const loading = current.state.status === "loading";
  // 로딩 중이거나 직전 요청이 실패했으면 아래 결과는 "이전 결과"로 흐리게 보여준다.
  const stale = loading || current.state.status === "error";
  const elapsed = useElapsedSeconds(ask.state.status === "loading");

  async function handleSubmit(text: string) {
    if (mode === "ask") {
      const result = await ask.run(text);
      if (result) setAnswered({ id: ++seqRef.current, question: text, result });
    } else {
      const result = await search.run(text);
      if (result) setSearched({ id: ++seqRef.current, query: text, result });
    }
  }

  return (
    <div className={styles.workspace}>
      <div className={styles.toolbar}>
        <ModeTabs value={mode} onChange={setMode} />
        <span className={styles.modeHint}>
          {mode === "ask" ? "노트에서 찾은 근거로 답하고 출처를 표시합니다" : "LLM 없이 관련 노트 조각만 찾습니다"}
        </span>
      </div>

      <QuestionForm
        placeholder={mode === "ask" ? "스터디 노트에 질문하기" : "검색어 입력"}
        submitLabel={mode === "ask" ? "질문" : "검색"}
        loading={loading}
        onSubmit={handleSubmit}
        onCancel={current.cancel}
      />

      <div className={styles.results} aria-live="polite" aria-busy={loading}>
        {loading && (
          <p className={styles.loading}>
            {mode === "ask" ? `노트를 찾고 답변을 만드는 중… ${elapsed}초` : "검색 중…"}
          </p>
        )}

        {current.state.status === "error" && <ErrorNotice error={current.state.error} />}

        {mode === "ask" && answered && (
          <div data-stale={stale || undefined} className={styles.result}>
            <AnswerPanel key={answered.id} question={answered.question} result={answered.result} />
          </div>
        )}

        {mode === "search" && searched && (
          <div data-stale={stale || undefined} className={styles.result}>
            <SearchResults key={searched.id} query={searched.query} results={searched.result.results} />
          </div>
        )}
      </div>
    </div>
  );
}
