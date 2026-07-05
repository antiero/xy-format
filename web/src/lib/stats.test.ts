import { afterEach, describe, expect, it, vi } from "vitest";
import {
  MAX_STEPS_PER_EVENT,
  fetchStats,
  normaliseConvertedSteps,
  reportConvertedSteps,
} from "./stats";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("normaliseConvertedSteps", () => {
  it("ignores invalid or non-positive values", () => {
    expect(normaliseConvertedSteps(Number.NaN)).toBeNull();
    expect(normaliseConvertedSteps(-1)).toBeNull();
    expect(normaliseConvertedSteps(0)).toBeNull();
  });

  it("floors and clamps valid values", () => {
    expect(normaliseConvertedSteps(12.8)).toBe(12);
    expect(normaliseConvertedSteps(MAX_STEPS_PER_EVENT + 500)).toBe(
      MAX_STEPS_PER_EVENT,
    );
  });
});

describe("fetchStats", () => {
  it("returns null when the stats request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    await expect(fetchStats()).resolves.toBeNull();
  });

  it("returns null for malformed payloads", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ totalSteps: "nope" }),
      }),
    );

    await expect(fetchStats()).resolves.toBeNull();
  });
});

describe("reportConvertedSteps", () => {
  it("does not report invalid counts", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await reportConvertedSteps(0);

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("reports only the clamped anonymous step count", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ totalSteps: 4096 }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await reportConvertedSteps(MAX_STEPS_PER_EVENT + 1);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/count-conversion",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ steps: MAX_STEPS_PER_EVENT }),
      }),
    );
  });

  it("swallows failed report requests", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    await expect(reportConvertedSteps(128)).resolves.toBeUndefined();
  });
});
