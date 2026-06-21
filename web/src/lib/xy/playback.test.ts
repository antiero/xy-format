import { describe, expect, it } from "vitest";
import { STEP_TICKS } from "./image_writer";
import {
  collectLanePlaybackEvents,
  collectScenePlaybackLanes,
  repeatPlaybackEvents,
  type PlaybackEvent,
} from "./playback";
import type {
  XYNoteViewModel,
  XYPatternViewModel,
  XYProjectViewModel,
  XYTrackScale,
  XYTrackViewModel,
} from "./projectViewModel";
import { noteName } from "./projectViewModel";

function note(id: string, tick: number, pitch = 60): XYNoteViewModel {
  return {
    id,
    noteIndex: 0,
    tick,
    displayTick: tick,
    displayStep: Math.round(tick / STEP_TICKS),
    gateTicks: STEP_TICKS,
    note: pitch,
    noteName: noteName(pitch),
    velocity: 100,
    flags0: 0,
    flags1: 0,
    start16ths: tick / STEP_TICKS,
    duration16ths: 1,
  };
}

function pattern(
  notes: XYNoteViewModel[],
  length16ths: number,
  trackScale: XYTrackScale,
  timingMode: XYPatternViewModel["timingMode"],
): XYPatternViewModel {
  return {
    index: 0,
    bars: Math.ceil(length16ths / 16),
    finalBarSteps: 16,
    totalSteps: 16,
    rawSteps: 16,
    trackScale,
    trackScaleRaw: 0x03,
    trackScaleLabel: trackScale,
    trackScaleKnown: true,
    trackScaleWriteSupported: true,
    timingMode,
    effectiveLength16ths: length16ths,
    notes,
    plocks: [],
    stepComponents: [],
  };
}

function track(
  index: number,
  patternValue: XYPatternViewModel,
): XYTrackViewModel {
  return {
    index,
    label: `T${index + 1}`,
    kind: "instrument",
    colorRole: "white",
    patterns: [patternValue],
  };
}

describe("playback scene repetition", () => {
  it("repeats shorter lane events through the scene loop", () => {
    const event: PlaybackEvent = {
      id: "t0:p0:n0",
      trackIndex: 0,
      patternIndex: 0,
      noteId: "n0",
      note: 60,
      velocity: 100,
      start16ths: 0,
      duration16ths: 1,
    };

    expect(
      repeatPlaybackEvents([event], 16, 48).map(
        (candidate) => candidate.start16ths,
      ),
    ).toEqual([0, 16, 32]);
  });

  it("keeps raw-timed long-track events while repeating shorter tracks", () => {
    const project = {
      tracks: [
        track(0, pattern([note("t0:p0:n0", 0)], 16, "1", "step")),
        track(
          7,
          pattern(
            [note("t7:p0:n0", 0, 69), note("t7:p0:n1", 680, 67)],
            64,
            "4",
            "raw",
          ),
        ),
      ],
      scenes: [
        {
          index: 0,
          present: true,
          patternByTrack: [0, 0, 0, 0, 0, 0, 0, 0],
          mutedTracks: [],
          length16ths: 64,
        },
      ],
      activeSceneIndex: 0,
    } as XYProjectViewModel;

    const lanes = collectScenePlaybackLanes(project, 0);
    const t1Events = lanes.find((lane) => lane.trackIndex === 0)?.events ?? [];
    const t8Events = lanes.find((lane) => lane.trackIndex === 7)?.events ?? [];

    expect(t1Events.map((event) => event.start16ths)).toEqual([0, 16, 32, 48]);
    expect(t8Events.map((event) => event.start16ths)).toHaveLength(2);
    expect(t8Events[0]?.start16ths).toBe(0);
    expect(t8Events[1]?.start16ths).toBeCloseTo(5.6666667);

    const sceneStarts = collectLanePlaybackEvents(lanes).map(
      (event) => event.start16ths,
    );
    expect(sceneStarts).toHaveLength(6);
    expect(sceneStarts[0]).toBe(0);
    expect(sceneStarts[1]).toBe(0);
    expect(sceneStarts[2]).toBeCloseTo(5.6666667);
    expect(sceneStarts.slice(3)).toEqual([16, 32, 48]);
  });
});
