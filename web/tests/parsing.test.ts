import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync } from "fs";
import { ImageProject } from "../src/lib/xy/image_writer";

describe(".xy parsing", () => {
  it("correctly parses step position and gate length for test files", () => {
    const files = readdirSync("../output")
      .filter((f) => f.match(/^\d{2}_pt/))
      .sort();

    for (const file of files) {
      const fileBytes = readFileSync(`../output/${file}`);
      const proj = ImageProject.fromBytes(new Uint8Array(fileBytes));
      const notes = proj.getNotes(3);

      expect(notes).toHaveLength(1);
      const note = notes[0];

      const match = file.match(/_s(\d+)_g(\d+)/);
      expect(match).not.toBeNull();

      if (match) {
        const stepStr = match[1];
        const gateStr = match[2];

        const step = parseInt(stepStr, 10);
        const gateSteps = parseInt(gateStr, 10);

        const expectedTick = (step - 1) * 480;

        let expectedGate = 0;
        if (gateSteps === 1) expectedGate = 240;
        else if (gateSteps === 2) expectedGate = 540;
        else if (gateSteps === 4) expectedGate = 1920;
        else if (gateSteps === 8) expectedGate = 3840;

        expect(note.tick, `File ${file} tick mismatch`).toBe(expectedTick);
        expect(note.gate, `File ${file} gate mismatch`).toBe(expectedGate);
      }
    }
  });

  it("correctly parses multiple patterns", () => {
    const fileBytes = readFileSync(
      `../output/mp2_v7_diag_t1both_dense_t3clone.xy`,
    );
    const proj = ImageProject.fromBytes(new Uint8Array(fileBytes));

    // Track 1 has 2 patterns
    const patternCountTrack1 = proj.getPatternCount(1);
    expect(patternCountTrack1).toBe(2);

    const notesT1P0 = proj.getNotes(1, 0);
    expect(notesT1P0.length).toBe(8);

    const notesT1P1 = proj.getNotes(1, 1);
    expect(notesT1P1.length).toBe(11);

    // Track 3 has 2 patterns
    const patternCountTrack3 = proj.getPatternCount(3);
    expect(patternCountTrack3).toBe(2);

    const notesT3P0 = proj.getNotes(3, 0);
    expect(notesT3P0.length).toBe(0);

    const notesT3P1 = proj.getNotes(3, 1);
    expect(notesT3P1.length).toBe(6);
  });
});
