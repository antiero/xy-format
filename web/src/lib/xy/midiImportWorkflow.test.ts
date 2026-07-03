import { describe, expect, it } from "vitest";
import { midiImportNeedsEditor } from "./midiImportWorkflow";

function summary(
  overrides: Partial<{
    isSelectionRecommended: boolean;
    rangeStart16ths: number;
    rangeEnd16ths: number;
    sourceTotal16ths: number;
    trackCount: number;
    maxInstrumentTracks: number;
    drumTrackCount: number;
  }> = {},
) {
  const values = {
    isSelectionRecommended: false,
    rangeStart16ths: 0,
    rangeEnd16ths: 64,
    sourceTotal16ths: 64,
    trackCount: 1,
    maxInstrumentTracks: 8,
    drumTrackCount: 0,
    ...overrides,
  };

  return {
    trackSelection: {
      isSelectionRecommended: values.isSelectionRecommended,
      rangeStart16ths: values.rangeStart16ths,
      rangeEnd16ths: values.rangeEnd16ths,
      sourceTotal16ths: values.sourceTotal16ths,
      tracks: Array.from({ length: values.trackCount }, (_, index) => ({
        isDrum: index < values.drumTrackCount,
      })),
      maxInstrumentTracks: values.maxInstrumentTracks,
    },
  };
}

describe("MIDI import workflow", () => {
  it("skips the editor when the complete MIDI already fits", () => {
    expect(midiImportNeedsEditor(summary())).toBe(false);
  });

  it("requires the editor when track selection is recommended", () => {
    expect(
      midiImportNeedsEditor(summary({ isSelectionRecommended: true })),
    ).toBe(true);
  });

  it("requires the editor when GM drum mapping can be adjusted", () => {
    expect(midiImportNeedsEditor(summary({ drumTrackCount: 1 }))).toBe(true);
  });

  it("requires the editor for a shortened MIDI range", () => {
    expect(midiImportNeedsEditor(summary({ rangeEnd16ths: 48 }))).toBe(true);
  });

  it("requires the editor when source tracks exceed capacity", () => {
    expect(midiImportNeedsEditor(summary({ trackCount: 9 }))).toBe(true);
  });
});
