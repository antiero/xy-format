import { existsSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { loadXYBytes } from "./projectLoader";

const BOND_PATH = "/Users/ant/Desktop/bond.xy";

describe.skipIf(!existsSync(BOND_PATH))("bond.xy import", () => {
  it("reads Scene 1 selected track scales from the shifted image layout", () => {
    const project = loadXYBytes(
      new Uint8Array(readFileSync(BOND_PATH)),
      "bond.xy",
    );
    const scene = project.scenes[0];
    const selectedScales = project.tracks
      .slice(0, 8)
      .map(
        (track) => track.patterns[scene.patternByTrack[track.index]].trackScale,
      );

    expect(selectedScales).toEqual(["1", "1", "4", "4", "1", "4", "8", "4"]);
    expect(project.tracks[0].patterns[0]).toMatchObject({
      rawSteps: 16,
      trackScaleRaw: 0x03,
      trackScale: "1",
    });
    expect(project.tracks[6].patterns[2]).toMatchObject({
      rawSteps: 16,
      trackScaleRaw: 0x0b,
      trackScale: "8",
    });
  });

  it("does not report the old shifted-offset validation errors", () => {
    const project = loadXYBytes(
      new Uint8Array(readFileSync(BOND_PATH)),
      "bond.xy",
    );
    const codes = project.validation.map((issue) => issue.code);

    expect(codes).not.toContain("pattern-length-range");
    expect(codes).not.toContain("track-scale-unknown");
    expect(codes).not.toContain("scene-missing-pattern");
  });
});
