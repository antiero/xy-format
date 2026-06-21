import { existsSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { loadXYBytes } from "./projectLoader";

const SPACEOPUS_PATH = "/Users/ant/Desktop/spaceopus.xy";

describe.skipIf(!existsSync(SPACEOPUS_PATH))("spaceopus.xy import", () => {
  it("reads T8 pattern 1 with track scale 4", () => {
    const project = loadXYBytes(
      new Uint8Array(readFileSync(SPACEOPUS_PATH)),
      "spaceopus.xy",
    );
    const pattern = project.tracks[7].patterns[0];

    expect(pattern.trackScaleRaw).toBe(0x07);
    expect(pattern.trackScale).toBe("4");
    expect(pattern.trackScaleLabel).toBe("4");
    expect(pattern.effectiveLength16ths).toBe(64);
    expect(project.scenes[0].length16ths).toBe(64);
  });
});
