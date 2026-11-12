/** FastAPI 백엔드 응답 타입. backend/ 의 Pydantic 스키마와 1:1로 맞춘다. */

export type SourceType = "study" | "journal" | "memo" | "en-docs" | "research";

export interface HealthResponse {
  status: string;
  db: boolean;
  llm_base_url: string;
  embed_base_url: string;
}

export interface StatsResponse {
  entries: number;
  chunks: number;
  by_source: Partial<Record<SourceType, number>> & Record<string, number>;
}

export interface IngestRequest {
  source_type: SourceType;
}

export interface IngestResponse {
  scanned: number;
  added: number;
  updated: number;
  unchanged: number;
  deleted: number;
  chunks_embedded: number;
}

/** 검색으로 찾은 청크 하나. */
export interface SearchHit {
  chunk_id: number;
  text: string;
  heading_path: string;
  file_path: string;
  score: number;
}

export interface SearchResponse {
  results: SearchHit[];
}

export interface AskRequest {
  question: string;
  k?: number;
}

/** 답변에 인용된 출처. 답변 본문의 [n] 표기와 `n`이 대응한다. */
export interface AskSource extends SearchHit {
  n: number;
}

export interface AskResponse {
  answer: string;
  sources: AskSource[];
}
