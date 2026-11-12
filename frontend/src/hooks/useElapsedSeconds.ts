"use client";

import { useEffect, useState } from "react";

/** active인 동안 경과 초를 센다. 로컬 LLM 대기 시간을 보여주는 용도. */
export function useElapsedSeconds(active: boolean): number {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (!active) return;
    const startedAt = Date.now();
    const id = window.setInterval(() => {
      setSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => {
      window.clearInterval(id);
      setSeconds(0);
    };
  }, [active]);

  return seconds;
}
