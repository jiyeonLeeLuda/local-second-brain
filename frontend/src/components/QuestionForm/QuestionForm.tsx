"use client";

import { useId, useState, type FormEvent, type KeyboardEvent } from "react";
import styles from "./QuestionForm.module.css";

interface QuestionFormProps {
  placeholder: string;
  submitLabel: string;
  loading: boolean;
  onSubmit: (text: string) => void;
  onCancel?: () => void;
}

export function QuestionForm({ placeholder, submitLabel, loading, onSubmit, onCancel }: QuestionFormProps) {
  const [text, setText] = useState("");
  const inputId = useId();
  const trimmed = text.trim();

  function submit() {
    if (!trimmed || loading) return;
    onSubmit(trimmed);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    submit();
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // 한글 IME 조합 중 Enter는 무시한다.
    if (e.nativeEvent.isComposing) return;
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <label htmlFor={inputId} className="visually-hidden">
        {placeholder}
      </label>
      <textarea
        id={inputId}
        className={styles.textarea}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={3}
        autoFocus
      />
      <div className={styles.actions}>
        <span className={styles.hint}>
          <kbd>⌘</kbd>/<kbd>Ctrl</kbd> + <kbd>Enter</kbd>
        </span>
        {loading && onCancel && (
          <button type="button" className={styles.secondary} onClick={onCancel}>
            취소
          </button>
        )}
        <button type="submit" className={styles.primary} disabled={!trimmed || loading}>
          {loading ? "처리 중…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
