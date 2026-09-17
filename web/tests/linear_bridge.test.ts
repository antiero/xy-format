import { describe, expect, it } from "vitest";
import { readFileSync } from "fs";
import { loadXYBytes } from "../src/lib/xy/projectLoader";
import {
  exportActiveSongData,
  buildLinearSequenceProject,
  type LinearSequencePayload,
} from "../src/lib/xy/linearBridge";

function loadBlankBytes(): Uint8Array {
  const bytes = readFileSync(
    new URL("../public/baselines/blank.xy", import.meta.url),
  );
  return new Uint8Array(bytes);
}

describe("Linear Piano Roll Bridge", () => {
  it("exports active song data correctly", () => {
    const bytes = loadBlankBytes();
    const project = loadXYBytes(bytes, "blank.xy");
    const exportedJSON = exportActiveSongData(project);
    const data = JSON.parse(exportedJSON);

    expect(data.fileName).toBe("blank.xy");
    expect(data.tempoBpm).toBeGreaterThan(0);
    expect(Array.isArray(data.scenes)).toBe(true);
    expect(data.tracks.length).toBe(16);
  });

  it("builds linear sequence project across scenes and tracks", () => {
    const bytes = loadBlankBytes();

    const payload: LinearSequencePayload = {
      tempoBPM: 132,
      bars: 8,
      sceneCount: 2,
      notes: [
        {
          scene: 0,
          track: 0,
          step: 1,
          tick: 0,
          note: 60,
          velocity: 110,
          length: 1.0,
        },
        {
          scene: 1,
          track: 0,
          step: 17,
          tick: 0,
          note: 67,
          velocity: 95,
          length: 2.0,
        },
      ],
    };

    const project = buildLinearSequenceProject(bytes, payload, "MySong.xy");

    expect(project.tempoBpm).toBe(132);
    expect(project.songs[0].sceneChain).toEqual([0, 1]);

    // Check notes on track 0, pattern 0 (scene 0)
    const t0p0Notes = project.tracks[0].patterns[0].notes;
    expect(t0p0Notes.length).toBe(1);
    expect(t0p0Notes[0].note).toBe(60);
    expect(t0p0Notes[0].velocity).toBe(110);

    // Check notes on track 0, pattern 1 (scene 1)
    const t0p1Notes = project.tracks[0].patterns[1].notes;
    expect(t0p1Notes.length).toBe(1);
    expect(t0p1Notes[0].note).toBe(67);
    expect(t0p1Notes[0].velocity).toBe(95);

    // Verify exportActiveSongData reflects the imported notes
    const exportedJSON = exportActiveSongData(project);
    const data = JSON.parse(exportedJSON);
    expect(data.sceneChain).toEqual([0, 1]);
    expect(data.tempoBpm).toBe(132);
  });
});
