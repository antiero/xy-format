export const MAX_STEPS_PER_EVENT = 4096;

const ALLOWED_ORIGINS = new Set([
  "https://xybuddy.xyz",
  "https://www.xybuddy.xyz",
  "http://localhost:3000",
  "http://localhost:4173",
  "http://localhost:5173",
  "http://localhost:5174",
  "http://127.0.0.1:4173",
  "http://127.0.0.1:5173",
  "http://127.0.0.1:5174",
]);

export function normaliseStepCount(value: unknown): number | null {
  const count = Number(value);
  if (!Number.isFinite(count)) return null;

  const steps = Math.floor(count);
  if (steps <= 0) return null;

  return Math.min(steps, MAX_STEPS_PER_EVENT);
}

export function corsHeaders(origin: string | null): Record<string, string> {
  const allowOrigin =
    origin && ALLOWED_ORIGINS.has(origin) ? origin : "https://xybuddy.xyz";

  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    Vary: "Origin",
  };
}
