"use client";

import { useCallback, useEffect } from "react";
import { useRequest } from "@/hooks/useRequest";
import { api } from "@/lib/api/client";
import type { HealthResponse, IngestResponse, StatsResponse } from "@/lib/api/types";
import { formatCount } from "@/lib/format";
import styles from "./StatusBar.module.css";

type Tone = "ok" | "warn" | "error" | "pending";

function healthSummary(status: string, data?: HealthResponse): { tone: Tone; label: string } {
  if (status === "loading" && !data) return { tone: "pending", label: "확인 중" };
  if (!data) return { tone: "error", label: "백엔드 연결 안 됨" };
  if (!data.db) return { tone: "warn", label: "DB 연결 안 됨" };
  return { tone: "ok", label: "연결됨" };
}

function StatsText({ stats }: { stats: StatsResponse }) {
  const breakdown = Object.entries(stats.by_source)
    .map(([source, count]) => `${source} ${formatCount(count)}`)
    .join(" · ");
  return (
    <span title={breakdown || undefined}>
      노트 {formatCount(stats.entries)}개 · 청크 {formatCount(stats.chunks)}개
    </span>
  );
}

function IngestSummary({ result }: { result: IngestResponse }) {
  const items: [string, number][] = [
    ["스캔", result.scanned],
    ["추가", result.added],
    ["변경", result.updated],
    ["그대로", result.unchanged],
    ["삭제", result.deleted],
    ["임베딩한 청크", result.chunks_embedded],
  ];
  return (
    <dl className={styles.ingest}>
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{formatCount(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

/** 하단 상태 표시줄: 백엔드/DB 상태, 인덱스 규모, 모델 서버 주소, 재인덱싱 */
export function StatusBar() {
  const health = useRequest(api.health);
  const stats = useRequest(api.stats);
  const ingest = useRequest(api.ingest);
  const { run: runHealth } = health;
  const { run: runStats } = stats;

  const refresh = useCallback(() => {
    void runHealth();
    void runStats();
  }, [runHealth, runStats]);

  useEffect(refresh, [refresh]);

  async function reindex() {
    const result = await ingest.run({ source_type: "study" });
    if (result) void runStats();
  }

  const summary = healthSummary(health.state.status, health.state.data);
  const healthData = health.state.data;
  const ingesting = ingest.state.status === "loading";

  return (
    <footer className={styles.bar}>
      <div className={styles.row}>
        <button
          type="button"
          className={styles.status}
          data-tone={summary.tone}
          onClick={refresh}
          title="상태 새로고침"
        >
          <span className={styles.dot} aria-hidden />
          {summary.label}
        </button>

        {stats.state.data && <StatsText stats={stats.state.data} />}

        {healthData && (
          <span className={styles.url} title={`임베딩: ${healthData.embed_base_url}`}>
            LLM <code>{healthData.llm_base_url}</code>
          </span>
        )}

        <button type="button" className={styles.reindex} onClick={reindex} disabled={ingesting}>
          {ingesting ? "인덱싱 중…" : "다시 인덱싱"}
        </button>
      </div>

      {ingest.state.status === "success" && <IngestSummary result={ingest.state.data} />}
      {ingest.state.status === "error" && (
        <p className={styles.error} role="alert">
          인덱싱 실패: {ingest.state.error.message}
        </p>
      )}
      {health.state.status === "error" && (
        <p className={styles.error}>{health.state.error.message}</p>
      )}
    </footer>
  );
}
