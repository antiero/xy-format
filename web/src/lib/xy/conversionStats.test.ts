import { describe, expect, it } from "vitest";
import {
  midiImportNoteCount,
  projectNoteCount,
  type ProjectNoteCountSource,
} from "./conversionStats";

function projectWithNoteCounts(counts: number[][]): ProjectNoteCountSource {
  return {
    tracks: counts.map((patterns) => ({
      patterns: patterns.map((count) => ({
        notes: Array.from({ length: count }),
      })),
    })),
  };
}

describe("projectNoteCount", () => {
  it("counts decoded OP-XY project notes", () => {
    expect(projectNoteCount(projectWithNoteCounts([[600], [250, 150]]))).toBe(
      1000,
    );
  });

  it("ignores missing projects", () => {
    expect(projectNoteCount(null)).toBe(0);
  });
});

describe("midiImportNoteCount", () => {
  it("counts MIDI notes added to a generated OP-XY project", () => {
    expect(midiImportNoteCount({ importedNotes: 2000 })).toBe(2000);
  });

  it("ignores invalid MIDI import counts", () => {
    expect(midiImportNoteCount(null)).toBe(0);
    expect(midiImportNoteCount({ importedNotes: -1 })).toBe(0);
  });
});
