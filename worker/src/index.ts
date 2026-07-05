import { corsHeaders, normaliseStepCount } from "./stats";

export interface Env {
  XYBUDDY_STATS: KVNamespace;
}

const TOTAL_STEPS_KEY = "stats:totalSteps";
const TOTAL_CONVERSIONS_KEY = "stats:totalConversions";
const MAX_REQUEST_BYTES = 1024;

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
