"use client";

import styles from "./ModeTabs.module.css";

export type Mode = "ask" | "search";

const MODES: { value: Mode; label: string; hint: string }[] = [
  { value: "ask", label: "질문하기", hint: "검색한 노트를 근거로 LLM이 답합니다" },
  { value: "search", label: "검색만", hint: "LLM 없이 관련 노트 조각만 찾습니다" },
];

interface ModeTabsProps {
  value: Mode;
  onChange: (mode: Mode) => void;
}

export function ModeTabs({ value, onChange }: ModeTabsProps) {
  return (
    <div className={styles.tabs} role="group" aria-label="모드">
      {MODES.map((mode) => (
        <button
          key={mode.value}
          type="button"
          aria-pressed={value === mode.value}
          title={mode.hint}
          className={styles.tab}
          onClick={() => onChange(mode.value)}
        >
          {mode.label}
        </button>
      ))}
    </div>
  );
}
