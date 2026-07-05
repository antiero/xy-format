export interface Env {
  XYBUDDY_STATS: KVNamespace;
}

export const MAX_STEPS_PER_EVENT = 4096;

const TOTAL_STEPS_KEY = "stats:totalSteps";
const TOTAL_CONVERSIONS_KEY = "stats:totalConversions";
const MAX_REQUEST_BYTES = 1024;
const ALLOWED_ORIGINS = new Set([
  "https://xybuddy.xyz",
  "https://www.xybuddy.xyz",
  "http://localhost:3000",
  "http://localhost:4173",
  "http://localhost:5173",
  "http://127.0.0.1:4173",
  "http://127.0.0.1:5173",
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

async function readCounter(kv: KVNamespace, key: string): Promise<number> {
  const value = Number(await kv.get(key));
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
}

async function writeCounter(
  kv: KVNamespace,
  key: string,
  value: number,
): Promise<void> {
  await kv.put(key, String(Math.max(0, Math.floor(value))));
}

function jsonResponse(
  body: unknown,
  status: number,
  headers: Record<string, string>,
): Response {
  return Response.json(body, { status, headers });
}

function requestBodyIsTooLarge(request: Request): boolean {
  const contentLength = Number(request.headers.get("content-length") ?? 0);
  return Number.isFinite(contentLength) && contentLength > MAX_REQUEST_BYTES;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const headers = corsHeaders(request.headers.get("Origin"));

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers });
    }

    if (url.pathname === "/api/stats" && request.method === "GET") {
      const totalSteps = await readCounter(env.XYBUDDY_STATS, TOTAL_STEPS_KEY);

      return jsonResponse(
        { totalSteps },
        200,
        {
          ...headers,
          "Cache-Control": "public, max-age=60",
        },
      );
    }

    if (url.pathname === "/api/count-conversion" && request.method === "POST") {
      if (requestBodyIsTooLarge(request)) {
        return jsonResponse({ ok: false }, 413, headers);
      }

      const body = await request.json().catch(() => null);
      const steps = normaliseStepCount(
        (body as { steps?: unknown } | null)?.steps,
      );

      if (!steps) {
        return jsonResponse({ ok: false }, 400, headers);
      }

      // KV updates are approximate under concurrent writes. This is an ambient
      // community counter, not billing, analytics, or user-specific state.
      const currentSteps = await readCounter(env.XYBUDDY_STATS, TOTAL_STEPS_KEY);
      const totalSteps = currentSteps + steps;
      await writeCounter(env.XYBUDDY_STATS, TOTAL_STEPS_KEY, totalSteps);

      const currentConversions = await readCounter(
        env.XYBUDDY_STATS,
        TOTAL_CONVERSIONS_KEY,
      );
      await writeCounter(
        env.XYBUDDY_STATS,
        TOTAL_CONVERSIONS_KEY,
        currentConversions + 1,
      );

      return jsonResponse({ ok: true, totalSteps }, 200, headers);
    }

    return new Response("Not found", { status: 404, headers });
  },
};
