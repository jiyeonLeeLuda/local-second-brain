import type {
  AskRequest,
  AskResponse,
  HealthResponse,
  IngestRequest,
  IngestResponse,
  SearchResponse,
  StatsResponse,
} from "./types";

/** 백엔드가 non-2xx를 돌려줬거나 네트워크 오류가 났을 때 던지는 에러. */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }

  /** 0 = 네트워크 오류 (백엔드에 닿지 못함) */
  get isNetworkError(): boolean {
    return this.status === 0;
  }
}

/** 브라우저는 같은 origin의 /api/* 를 호출하고 next.config.ts rewrites가 백엔드로 프록시한다. */
const BASE = "/api";

interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  signal?: AbortSignal;
}

async function readErrorDetail(res: Response): Promise<string> {
  try {
    const data: unknown = await res.json();
    if (data && typeof data === "object" && "detail" in data) {
      const { detail } = data as { detail: unknown };
      if (typeof detail === "string") return detail;
      // FastAPI 422 검증 오류는 detail이 배열로 온다.
      if (Array.isArray(detail)) {
        return detail
          .map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d)))
          .join(", ");
      }
    }
  } catch {
    // JSON이 아닌 응답 (예: 프록시가 반환한 HTML 오류 페이지)
  }
  if (res.status >= 500 && res.status !== 503) {
    return `백엔드 서버 오류가 발생했습니다 (${res.status}).`;
  }
  return res.statusText || `요청이 실패했습니다 (${res.status}).`;
}

async function request<T>(path: string, { method = "GET", body, signal }: RequestOptions = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      signal,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError("백엔드 서버에 연결할 수 없습니다.", 0);
  }

  if (!res.ok) {
    throw new ApiError(await readErrorDetail(res), res.status);
  }
  return (await res.json()) as T;
}

export const api = {
  health: (signal?: AbortSignal) => request<HealthResponse>("/health", { signal }),

  stats: (signal?: AbortSignal) => request<StatsResponse>("/stats", { signal }),

  ingest: (body: IngestRequest, signal?: AbortSignal) =>
    request<IngestResponse>("/ingest", { method: "POST", body, signal }),

  search: (q: string, k = 5, signal?: AbortSignal) => {
    const params = new URLSearchParams({ q, k: String(k) });
    return request<SearchResponse>(`/search?${params}`, { signal });
  },

  ask: (body: AskRequest, signal?: AbortSignal) =>
    request<AskResponse>("/ask", { method: "POST", body, signal }),
};

export function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === "AbortError";
}

/** UI에 보여줄 에러 문구 */
export function toErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "알 수 없는 오류가 발생했습니다.";
}
