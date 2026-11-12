import type { RequestFailure } from "@/hooks/useRequest";
import styles from "./ErrorNotice.module.css";

function titleFor({ status }: RequestFailure): string {
  if (status === 0) return "백엔드 서버에 연결할 수 없습니다";
  if (status === 503) return "모델 서버에 연결할 수 없습니다";
  if (status !== undefined && status >= 400 && status < 500) return "요청을 처리할 수 없습니다";
  return "오류가 발생했습니다";
}

function hintFor({ status }: RequestFailure): string | null {
  if (status === 0) return "FastAPI 백엔드가 실행 중인지, BACKEND_URL 설정이 맞는지 확인해 주세요.";
  if (status === 503) return "LLM 추론 서버(LLM_BASE_URL)가 켜져 있는지 확인해 주세요. '검색만' 모드는 LLM 없이 동작합니다.";
  return null;
}

export function ErrorNotice({ error }: { error: RequestFailure }) {
  const hint = hintFor(error);
  return (
    <div className={styles.notice} role="alert">
      <p className={styles.title}>{titleFor(error)}</p>
      <p className={styles.detail}>{error.message}</p>
      {hint && <p className={styles.hint}>{hint}</p>}
    </div>
  );
}
