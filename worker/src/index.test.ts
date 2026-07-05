import { describe, expect, it } from "vitest";
import worker, {
  type Env,
} from "./index";
import {
  MAX_STEPS_PER_EVENT,
  corsHeaders,
  normaliseStepCount,
} from "./stats";

class MemoryKV {
  private store = new Map<string, string>();

  async get(key: string): Promise<string | null> {
    return this.store.get(key) ?? null;
  }

  async put(key: string, value: string): Promise<void> {
    this.store.set(key, value);
  }
}

function testEnv(): Env {
  return {
    XYBUDDY_STATS: new MemoryKV() as unknown as KVNamespace,
  };
}

function jsonRequest(path: string, body: unknown): Request {
  return new Request(`https://api.xybuddy.xyz${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: "https://xybuddy.xyz",
    },
    body: JSON.stringify(body),
  });
}

describe("normaliseStepCount", () => {
  it("rejects invalid step counts", () => {
    expect(normaliseStepCount(Number.NaN)).toBeNull();
    expect(normaliseStepCount(-4)).toBeNull();
    expect(normaliseStepCount(0)).toBeNull();
  });

  it("floors and clamps valid step counts", () => {
    expect(normaliseStepCount(99.9)).toBe(99);
    expect(normaliseStepCount(MAX_STEPS_PER_EVENT + 50)).toBe(
      MAX_STEPS_PER_EVENT,
    );
  });
});

describe("corsHeaders", () => {
  it("allows production and local development origins", () => {
    expect(corsHeaders("https://xybuddy.xyz")).toMatchObject({
      "Access-Control-Allow-Origin": "https://xybuddy.xyz",
    });
    expect(corsHeaders("http://localhost:5173")).toMatchObject({
      "Access-Control-Allow-Origin": "http://localhost:5173",
    });
    expect(corsHeaders("http://127.0.0.1:5174")).toMatchObject({
      "Access-Control-Allow-Origin": "http://127.0.0.1:5174",
    });
  });

  it("does not echo disallowed origins", () => {
    expect(corsHeaders("https://example.com")).toMatchObject({
      "Access-Control-Allow-Origin": "https://xybuddy.xyz",
    });
  });
});

describe("stats worker", () => {
  it("returns zero stats before any conversions", async () => {
    const response = await worker.fetch(
      new Request("https://api.xybuddy.xyz/api/stats"),
      testEnv(),
    );

    await expect(response.json()).resolves.toEqual({ totalSteps: 0 });
  });

  it("increments total steps on conversion reports", async () => {
    const env = testEnv();
    const postResponse = await worker.fetch(
      jsonRequest("/api/count-conversion", { steps: 128 }),
      env,
    );
    const getResponse = await worker.fetch(
      new Request("https://api.xybuddy.xyz/api/stats"),
      env,
    );

    expect(postResponse.status).toBe(200);
    await expect(postResponse.json()).resolves.toEqual({
      ok: true,
      totalSteps: 128,
    });
    await expect(getResponse.json()).resolves.toEqual({ totalSteps: 128 });
  });

  it("rejects invalid input", async () => {
    const response = await worker.fetch(
      jsonRequest("/api/count-conversion", { steps: -1 }),
      testEnv(),
    );

    expect(response.status).toBe(400);
  });

  it("clamps oversized reports", async () => {
    const response = await worker.fetch(
      jsonRequest("/api/count-conversion", {
        steps: MAX_STEPS_PER_EVENT + 1,
      }),
      testEnv(),
    );

    await expect(response.json()).resolves.toEqual({
      ok: true,
      totalSteps: MAX_STEPS_PER_EVENT,
    });
  });

  it("handles preflight requests", async () => {
    const response = await worker.fetch(
      new Request("https://api.xybuddy.xyz/api/count-conversion", {
        method: "OPTIONS",
        headers: { Origin: "https://xybuddy.xyz" },
      }),
      testEnv(),
    );

    expect(response.status).toBe(204);
    expect(response.headers.get("Access-Control-Allow-Origin")).toBe(
      "https://xybuddy.xyz",
    );
  });
});
