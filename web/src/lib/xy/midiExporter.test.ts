import { Midi } from "@tonejs/midi";
import { describe, expect, it } from "vitest";
import { STEP_TICKS } from "./image_writer";
import {
  exportSongMidi,
  exportPatternMidis,
  exportTrackMidis,
  exportableMidiNoteCount,
} from "./midiExporter";
import type {
  XYNoteViewModel,
  XYPatternViewModel,
  XYProjectViewModel,
  XYSceneViewModel,
  XYTrackViewModel,
} from "./projectViewModel";
import { noteName } from "./projectViewModel";

function note(id: string, pitch: number, tick = 0): XYNoteViewModel {
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
  index: number,
  notes: XYNoteViewModel[] = [],
  length16ths = 16,
): XYPatternViewModel {
  return {
    index,
    bars: Math.ceil(length16ths / 16),
    finalBarSteps: 16,
    totalSteps: 16,
    rawSteps: 16,
    trackScale: "1",
    trackScaleRaw: 0x03,
    trackScaleLabel: "1",
    trackScaleKnown: true,
    trackScaleWriteSupported: true,
    timingMode: "step",
    effectiveLength16ths: length16ths,
    notes,
    plocks: [],
    stepComponents: [],
  };
}

function track(
  index: number,
  patterns: XYPatternViewModel[] = [pattern(0)],
): XYTrackViewModel {
  return {
    index,
    label: `T${index + 1}`,
    kind: index < 8 ? "instrument" : "aux",
    colorRole: "white",
    patterns,
  };
}

function scene(
  index: number,
  length16ths: number,
  mutedTracks: number[] = [],
): XYSceneViewModel {
  return {
    index,
    present: true,
    patternByTrack: Array(16).fill(0),
    mutedTracks: Array.from({ length: 16 }, (_, trackIndex) =>
      mutedTracks.includes(trackIndex),
    ),
    length16ths,
  };
}

function project({
  tracks,
  scenes = [scene(0, 16)],
  tempoBpm = 123,
}: {
  tracks: XYTrackViewModel[];
  scenes?: XYSceneViewModel[];
  tempoBpm?: number;
}): XYProjectViewModel {
  const tracksByIndex = new Map(
    tracks.map((candidate) => [candidate.index, candidate]),
  );

  return {
    fileName: "test.xy",
    modified: false,
    tempoBpm,
    validation: [],
    tracks: Array.from(
      { length: 16 },
      (_, index) => tracksByIndex.get(index) ?? track(index),
    ),
    scenes,
    songs: [{ index: 0, sceneChain: [0], loop: true, supported: true }],
    activeTrackIndex: 0,
    activePatternIndex: 0,
    activeSceneIndex: 0,
    imageProject: null as never,
  };
}

describe("MIDI song export", () => {
  it("writes the edited project tempo into exported MIDI", () => {
    const exported = exportSongMidi(
      project({
        tempoBpm: 178.5,
        tracks: [track(0, [pattern(0, [note("bd", 53)])])],
      }),
      "tempo.xy",
    );
    const midi = new Midi(exported.bytes);

    expect(midi.header.tempos[0]?.bpm).toBeCloseTo(178.5, 1);
  });

  it("exports instrument tracks with OP-XY drum tracks on channel 10", () => {
    const exported = exportSongMidi(
      project({
        tracks: [
          track(0, [pattern(0, [note("bd", 53)])]),
          track(1),
          track(2, [pattern(0, [note("lead", 60)])]),
        ],
      }),
      "demo.xy",
    );
    const midi = new Midi(exported.bytes);

    expect(exported.filename).toBe("demo.mid");
    expect(midi.header.ppq).toBe(STEP_TICKS * 4);
    expect(midi.tracks).toHaveLength(2);
    expect(midi.tracks[0].channel).toBe(9);
    expect(midi.tracks[0].notes[0].midi).toBe(36);
    expect(midi.tracks[1].channel).toBe(2);
    expect(midi.tracks[1].notes[0].midi).toBe(60);
  });

  it("does not export notes from muted scene tracks", () => {
    const exported = exportSongMidi(
      project({
        tracks: [
          track(0, [pattern(0, [note("muted", 53)])]),
          track(1),
          track(2, [pattern(0, [note("audible", 60)])]),
        ],
        scenes: [scene(0, 16, [0])],
      }),
    );
    const midi = new Midi(exported.bytes);

    expect(exported.noteCount).toBe(1);
    expect(midi.tracks).toHaveLength(1);
    expect(midi.tracks[0].channel).toBe(2);
  });

  it("can include disabled scene tracks when requested", () => {
    const exported = exportSongMidi(
      project({
        tracks: [
          track(0, [pattern(0, [note("muted", 53)])]),
          track(1),
          track(2, [pattern(0, [note("audible", 60)])]),
        ],
        scenes: [scene(0, 16, [0])],
      }),
      "disabled.xy",
      { includeDisabledTracks: true },
    );
    const midi = new Midi(exported.bytes);

    expect(exported.noteCount).toBe(2);
    expect(midi.tracks.map((candidate) => candidate.channel)).toEqual([9, 2]);
  });

  it("exports repeated shorter patterns through longer scenes", () => {
    const exported = exportSongMidi(
      project({
        tracks: [
          track(0),
          track(1),
          track(2, [pattern(0, [note("c", 60)], 16)]),
        ],
        scenes: [scene(0, 32)],
      }),
    );
    const midi = new Midi(exported.bytes);

    expect(midi.tracks[0].notes.map((candidate) => candidate.ticks)).toEqual([
      0,
      16 * STEP_TICKS,
    ]);
  });

  it("reports exportable notes only for instrument tracks", () => {
    const testProject = project({
      tracks: [
        track(0, [pattern(0, [note("bd", 53)])]),
        track(8, [pattern(0, [note("aux", 72)])]),
      ],
    });

    expect(exportableMidiNoteCount(testProject)).toBe(1);
  });
});

describe("MIDI track export", () => {
  it("creates one MIDI file per non-empty instrument track", () => {
    const files = exportTrackMidis(
      project({
        tracks: [
          track(0, [pattern(0, [note("bd", 53)])]),
          track(1),
          track(2, [pattern(0, [note("lead", 60)])]),
        ],
      }),
    );

    expect(files.map((file) => file.filename)).toEqual([
      "track1.mid",
      "track3.mid",
    ]);
    expect(files.map((file) => file.trackIndexes)).toEqual([[0], [2]]);
  });
});

describe("MIDI pattern export", () => {
  it("creates one MIDI file per non-empty instrument pattern", () => {
    const testProject = project({
      tracks: [
        track(0, [pattern(0, [note("bd", 53)]), pattern(1, [note("sn", 56)])]),
        track(2, [pattern(0), pattern(1), pattern(2, [note("lead", 60)])]),
        track(8, [pattern(0, [note("aux", 72)])]),
      ],
    });
    testProject.scenes[0].patternByTrack[2] = 2;
    const files = exportPatternMidis(testProject, "project_name.xy");

    expect(files.map((file) => file.filename)).toEqual([
      "project_name-trk1-pt-1.mid",
      "project_name-trk1-pt-2.mid",
      "project_name-trk3-pt-3.mid",
    ]);
    expect(files.map((file) => file.trackIndexes)).toEqual([[0], [0], [2]]);

    const firstMidi = new Midi(files[0].bytes);
    expect(firstMidi.tracks[0].channel).toBe(9);
    expect(firstMidi.tracks[0].notes[0].midi).toBe(36);
  });

  it("only includes disabled track patterns when requested", () => {
    const testProject = project({
      tracks: [
        track(0, [pattern(0, [note("muted", 53)])]),
        track(2, [pattern(0, [note("lead", 60)])]),
      ],
      scenes: [scene(0, 16, [0])],
    });

    expect(
      exportPatternMidis(testProject, "disabled.xy").map(
        (file) => file.filename,
      ),
    ).toEqual(["disabled-trk3-pt-1.mid"]);
    expect(
      exportPatternMidis(testProject, "disabled.xy", {
        includeDisabledTracks: true,
      }).map((file) => file.filename),
    ).toEqual(["disabled-trk1-pt-1.mid", "disabled-trk3-pt-1.mid"]);
  });
});
