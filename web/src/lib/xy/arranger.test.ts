import { describe, expect, it } from "vitest";
import {
  ARRANGER_PATTERN_ROWS,
  ARRANGER_CENTER_ROW,
  buildArrangerFrame,
  buildArrangerSequence,
} from "./arranger";
import type {
  XYSongViewModel,
  XYNoteViewModel,
  XYPatternViewModel,
  XYProjectViewModel,
  XYSceneViewModel,
  XYTrackViewModel,
} from "./projectViewModel";
import { noteName } from "./projectViewModel";

function note(id: string, pitch = 60): XYNoteViewModel {
  return {
    id,
    noteIndex: 0,
    tick: 0,
    displayTick: 0,
    displayStep: 0,
    gateTicks: 480,
    note: pitch,
    noteName: noteName(pitch),
    velocity: 100,
    flags0: 0,
    flags1: 0,
    start16ths: 0,
    duration16ths: 1,
  };
}

function pattern(
  index: number,
  notes: XYNoteViewModel[] = [],
): XYPatternViewModel {
  return {
    index,
    bars: 1,
    finalBarSteps: 16,
    totalSteps: 16,
    rawSteps: 16,
    trackScale: "1",
    trackScaleRaw: 0x03,
    trackScaleLabel: "1",
    trackScaleKnown: true,
    trackScaleWriteSupported: true,
    timingMode: "step",
    effectiveLength16ths: 16,
    notes,
    plocks: [],
    stepComponents: [],
  };
}

function track(index: number, patternCount = 3): XYTrackViewModel {
  return {
    index,
    label: `T${index + 1}`,
    kind: index < 8 ? "instrument" : "aux",
    colorRole: "white",
    patterns: Array.from({ length: patternCount }, (_, patternIndex) =>
      pattern(
        patternIndex,
        index === 0 && patternIndex === 1 ? [note("kick", 53)] : [],
      ),
    ),
  };
}

function scene(
  index: number,
  present: boolean,
  patternByTrack: number[] = [],
): XYSceneViewModel {
  return {
    index,
    present,
    patternByTrack: Array.from(
      { length: 16 },
      (_, trackIndex) => patternByTrack[trackIndex] ?? 0,
    ),
    mutedTracks: Array(16).fill(false),
    length16ths: 16,
  };
}

function project({
  scenes = [scene(0, true)],
  song = { index: 0, sceneChain: [], loop: true, supported: true },
}: {
  scenes?: XYSceneViewModel[];
  song?: XYSongViewModel;
} = {}): XYProjectViewModel {
  return {
    fileName: "test.xy",
    modified: false,
    tempoBpm: 120,
    validation: [],
    tracks: Array.from({ length: 16 }, (_, index) => track(index, 5)),
    scenes,
    songs: [song],
    activeTrackIndex: 0,
    activePatternIndex: 0,
    activeSceneIndex: 0,
    imageProject: null as never,
  };
}

describe("arranger sequence", () => {
  it("uses Song 1 scene order when a supported chain exists", () => {
    const result = buildArrangerSequence(
      project({
        scenes: [scene(0, true), scene(1, true), scene(2, true)],
        song: { index: 0, sceneChain: [2, 0], loop: true, supported: true },
      }),
    );

    expect(result.source).toBe("song");
    expect(result.sceneIndexes).toEqual([2, 0]);
  });

  it("falls back to present scenes when Song 1 is empty", () => {
    const result = buildArrangerSequence(
      project({
        scenes: [scene(0, true), scene(1, false), scene(2, true)],
      }),
    );

    expect(result.source).toBe("scenes");
    expect(result.sceneIndexes).toEqual([0, 2]);
  });
});

describe("arranger frame", () => {
  it("centers each scene's active pattern in the track column", () => {
    const frame = buildArrangerFrame(
      project({
        scenes: [scene(0, true, [2])],
      }),
      0,
    );

    const t1 = frame.columns[0];
    expect(t1.activePatternIndex).toBe(2);
    expect(t1.slots[ARRANGER_CENTER_ROW].patternIndex).toBe(2);
    expect(t1.slots[ARRANGER_CENTER_ROW].active).toBe(true);
    expect(t1.slots[ARRANGER_CENTER_ROW - 2].patternIndex).toBe(0);
    expect(t1.slots[ARRANGER_CENTER_ROW + 2].patternIndex).toBe(4);
  });

  it("keeps the first pattern visible in the arranger window", () => {
    const frame = buildArrangerFrame(
      project({
        scenes: [scene(0, true, [0])],
      }),
      0,
    );

    const t1 = frame.columns[0];
    expect(t1.slots).toHaveLength(ARRANGER_PATTERN_ROWS);
    expect(t1.slots[ARRANGER_CENTER_ROW]).toMatchObject({
      patternIndex: 0,
      active: true,
      exists: true,
    });
  });

  it("exposes only the 8 OP-XY instrument tracks", () => {
    const frame = buildArrangerFrame(project(), 0);

    expect(frame.columns).toHaveLength(8);
    expect(frame.columns.map((column) => column.trackIndex)).toEqual([
      0, 1, 2, 3, 4, 5, 6, 7,
    ]);
  });
});
