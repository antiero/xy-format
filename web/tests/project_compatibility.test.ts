import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { loadXYFile } from "../src/lib/xy/projectLoader";

const baseline = new Uint8Array(
  readFileSync(new URL("../public/baselines/blank.xy", import.meta.url)),
);

describe("project compatibility gate", () => {
  it("opens a proven layout for editing", async () => {
    const result = await loadXYFile(new File([baseline], "blank.xy"));

    expect(result.kind).toBe("editable");
    expect(result.assessment.status).toBe("knownCompatible");
    expect(result.assessment.trackCount).toBe(16);
  });

  it("keeps an unknown firmware header read-only and byte exact", async () => {
    const unknown = baseline.slice();
    unknown[4] ^= 0xff;

    const result = await loadXYFile(new File([unknown], "future.xy"));

    expect(result.kind).toBe("diagnostic");
    if (result.kind === "diagnostic") {
      expect(result.assessment.status).toBe("unknownFirmware");
      expect(result.originalBytes).toEqual(unknown);
    }
  });
});
