export const MIN_PROJECT_TEMPO_BPM = 40;
export const MAX_PROJECT_TEMPO_BPM = 220;

export function normalizeProjectTempoBpm(
  value: number,
  fallback = 120,
): number {
  const finiteValue = Number.isFinite(value) ? value : fallback;
  const clamped = Math.max(
    MIN_PROJECT_TEMPO_BPM,
    Math.min(MAX_PROJECT_TEMPO_BPM, finiteValue),
  );
  return Math.round(clamped * 10) / 10;
}
