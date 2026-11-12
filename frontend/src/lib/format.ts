/** "notes/study/react/hooks.md" -> "hooks.md" */
export function basename(path: string): string {
  const parts = path.split(/[\\/]/);
  return parts[parts.length - 1] || path;
}

/** "notes/study/react/hooks.md" -> "notes/study/react" */
export function dirname(path: string): string {
  const idx = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
  return idx > 0 ? path.slice(0, idx) : "";
}

export function formatScore(score: number): string {
  return Number.isFinite(score) ? score.toFixed(3) : "-";
}

const numberFormat = new Intl.NumberFormat("ko-KR");

export function formatCount(n: number): string {
  return numberFormat.format(n);
}
