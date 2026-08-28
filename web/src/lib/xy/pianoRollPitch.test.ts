import { describe, expect, it } from "vitest";
import {
  collapsedRowIndex,
  expandedPianoRollPitches,
  movePitchByVisibleRows,
  usedPianoRollPitches,
  visiblePianoRollPitches,
} from "./pianoRollPitch";

describe("piano-roll pitch layout", () => {
  it("keeps the expanded chromatic range around used notes", () => {
    const pitches = expandedPianoRollPitches([67, 50]);

    expect(pitches[0]).toBe(72);
    expect(pitches.at(-1)).toBe(45);
    expect(pitches).toHaveLength(28);
  });

  it("shows each used pitch once in descending order", () => {
    expect(usedPianoRollPitches([50, 67, 50, 55])).toEqual([67, 55, 50]);
    expect(visiblePianoRollPitches([50, 67, 50], "used")).toEqual([67, 50]);
  });

  it("falls back to an editable range when an empty pattern is compacted", () => {
    expect(visiblePianoRollPitches([], "used")).toEqual(
      expandedPianoRollPitches([]),
    );
  });

  it("collapses unused pitches toward their nearest insertion row", () => {
    expect(collapsedRowIndex(70, [72, 67, 50])).toBe(1);
    expect(collapsedRowIndex(54, [72, 67, 50])).toBe(2);
    expect(collapsedRowIndex(40, [72, 67, 50])).toBe(3);
  });

  it("moves notes between visible rows when compacted", () => {
    const visible = [67, 55, 50];

    expect(movePitchByVisibleRows(67, 1, visible)).toBe(55);
    expect(movePitchByVisibleRows(55, -1, visible)).toBe(67);
    expect(movePitchByVisibleRows(50, 4, visible)).toBe(50);
  });
});
