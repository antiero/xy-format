export type XYBuddyStats = {
  totalSteps: number;
};

export const MAX_STEPS_PER_EVENT = 4096;

const STATS_API_BASE = import.meta.env.VITE_STATS_API_BASE ?? "";
const STATS_UPDATED_EVENT = "xybuddy-stats-updated";

function statsUrl(path: string): string {
  return `${STATS_API_BASE}${path}`;
}

export function normaliseConvertedSteps(value: unknown): number | null {
  const count = Number(value);
  if (!Number.isFinite(count)) return null;

  const steps = Math.floor(count);
  if (steps <= 0) return null;

  return Math.min(steps, MAX_STEPS_PER_EVENT);
}

function parseStatsPayload(value: unknown): XYBuddyStats | null {
  if (!value || typeof value !== "object") return null;

  const totalSteps = Number((value as { totalSteps?: unknown }).totalSteps);
  if (!Number.isFinite(totalSteps) || totalSteps < 0) return null;

  return { totalSteps: Math.floor(totalSteps) };
}

function notifyStatsUpdated(stats: XYBuddyStats): void {
  if (typeof window === "undefined") return;

  window.dispatchEvent(new CustomEvent(STATS_UPDATED_EVENT, { detail: stats }));
}

export async function fetchStats(): Promise<XYBuddyStats | null> {
  try {
    const response = await fetch(statsUrl("/api/stats"), {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) return null;

    return parseStatsPayload(await response.json());
  } catch {
    return null;
  }
}

export async function reportConvertedSteps(steps: number): Promise<void> {
  const convertedSteps = normaliseConvertedSteps(steps);
  if (!convertedSteps) return;

  try {
    const response = await fetch(statsUrl("/api/count-conversion"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ steps: convertedSteps }),
      keepalive: true,
    });

    if (!response.ok) return;

    const stats = parseStatsPayload(await response.json().catch(() => null));
    if (stats) notifyStatsUpdated(stats);
  } catch {
    // Anonymous aggregate stats are non-critical and must not affect conversion.
  }
}

export { STATS_UPDATED_EVENT };
