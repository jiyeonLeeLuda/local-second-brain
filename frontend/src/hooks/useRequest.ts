"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, isAbortError, toErrorMessage } from "@/lib/api/client";

export interface RequestFailure {
  message: string;
  /** HTTP 상태 코드. 0 = 네트워크 오류, undefined = 알 수 없음 */
  status?: number;
}

export type RequestState<T> =
  | { status: "idle"; data?: undefined; error?: undefined }
  | { status: "loading"; data?: T; error?: undefined }
  | { status: "success"; data: T; error?: undefined }
  | { status: "error"; data?: undefined; error: RequestFailure };

/**
 * 비동기 요청 하나의 상태(idle/loading/success/error)를 관리한다.
 * 새 요청을 시작하면 이전 요청은 abort되어 늦게 도착한 응답이 화면을 덮어쓰지 않는다.
 */
export function useRequest<TArgs extends unknown[], T>(
  fn: (...args: [...TArgs, AbortSignal]) => Promise<T>,
) {
  const [state, setState] = useState<RequestState<T>>({ status: "idle" });
  const controllerRef = useRef<AbortController | null>(null);
  const fnRef = useRef(fn);

  useEffect(() => {
    fnRef.current = fn;
  }, [fn]);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const run = useCallback(async (...args: TArgs): Promise<T | undefined> => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    // 이전 결과는 로딩 중에도 유지해 화면이 깜빡이지 않게 한다.
    setState((prev) => ({ status: "loading", data: prev.data }));
    try {
      const data = await fnRef.current(...args, controller.signal);
      if (controller.signal.aborted) return undefined;
      setState({ status: "success", data });
      return data;
    } catch (err) {
      if (isAbortError(err) || controller.signal.aborted) return undefined;
      setState({
        status: "error",
        error: {
          message: toErrorMessage(err),
          status: err instanceof ApiError ? err.status : undefined,
        },
      });
      return undefined;
    }
  }, []);

  const cancel = useCallback(() => {
    controllerRef.current?.abort();
    setState((prev) => (prev.status === "loading" ? { status: "idle" } : prev));
  }, []);

  return { state, run, cancel };
}
