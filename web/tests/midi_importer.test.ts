import { describe, expect, it } from "vitest";
import { readFileSync } from "fs";
import { writeMidi, type MidiData, type MidiEvent } from "midi-file";
import { buildMidiProjectFromBytes } from "../src/lib/xy/midiImporter";

const BASELINE = "../src/one-off-changes-from-default/unnamed 1.xy";

function makeTrackFromAbsolute(
  events: Array<{ tick: number; event: Omit<MidiEvent, "deltaTime"> }>,
): MidiEvent[] {
  const sorted = [...events].sort(
    (a, b) => a.tick - b.tick || (a.event.type === "noteOff" ? -1 : 1),
  );
  let lastTick = 0;
  return sorted.map(({ tick, event }) => {
    const deltaTime = tick - lastTick;
    lastTick = tick;
    return { ...event, deltaTime } as MidiEvent;
  });
}

function singlePolyphonicLaneMidi(): Uint8Array {
  const tpb = 480;
  const bar = tpb * 4;
  const noteEvents: Array<{
    tick: number;
    event: Omit<MidiEvent, "deltaTime">;
  }> = [];
  const voicings = [
    [60, 64, 67],
    [57, 60, 64],
    [62, 65, 69],
    [55, 59, 62],
  ];

  for (let b = 0; b < 8; b++) {
    for (const beat of [0, 2]) {
      const onset = b * bar + beat * tpb;
      for (const pitch of voicings[b % voicings.length]) {
        noteEvents.push({
          tick: onset,
          event: {
            type: "noteOn",
            channel: 7,
            noteNumber: pitch,
            velocity: 86,
          },
        });
        noteEvents.push({
          tick: onset + tpb * 2,
          event: {
            type: "noteOff",
            channel: 7,
            noteNumber: pitch,
            velocity: 0,
          },
        });
      }
    }
  }

  const data: MidiData = {
    header: { format: 1, numTracks: 2, ticksPerBeat: tpb },
    tracks: [
      [
        {
          deltaTime: 0,
          type: "setTempo",
          meta: true,
          microsecondsPerBeat: Math.round(60_000_000 / 98),
        },
        { deltaTime: 0, type: "endOfTrack", meta: true },
      ],
      [
        ...makeTrackFromAbsolute(noteEvents),
        { deltaTime: 0, type: "endOfTrack", meta: true },
      ],
    ],
  };
  return new Uint8Array(writeMidi(data));
}

function oneBarDrumMidi(): Uint8Array {
  const tpb = 480;
  const noteEvents: Array<{
    tick: number;
    event: Omit<MidiEvent, "deltaTime">;
  }> = [];

  for (const tick of [0, 480, 960, 1440, 1800]) {
    const noteNumber = tick % 960 === 0 ? 36 : 42;
    noteEvents.push(
      {
        tick,
        event: {
          type: "noteOn",
          channel: 9,
          noteNumber,
          velocity: 114,
        },
      },
      {
        tick: tick + 90,
        event: {
          type: "noteOff",
          channel: 9,
          noteNumber,
          velocity: 0,
        },
      },
    );
  }

  const data: MidiData = {
    header: { format: 0, numTracks: 1, ticksPerBeat: tpb },
    tracks: [
      [
        {
          deltaTime: 0,
          type: "setTempo",
          meta: true,
          microsecondsPerBeat: 500_000,
        },
        ...makeTrackFromAbsolute(noteEvents),
        { deltaTime: 30, type: "endOfTrack", meta: true },
      ],
    ],
  };
  return new Uint8Array(writeMidi(data));
}

function longDistinctDrumMidi(patternCount = 17): Uint8Array {
  const tpb = 480;
  const bar = tpb * 4;
  const noteEvents: Array<{
    tick: number;
    event: Omit<MidiEvent, "deltaTime">;
  }> = [];
  const accentNotes = [
    36, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53,
  ];

  // Distinct 4-bar windows. Seventeen exceeds one track's 16-pattern limit,
  // so the importer must place the final window in a muted bank on a spare
  // instrument track while retaining every Song scene.
  for (let pattern = 0; pattern < patternCount; pattern++) {
    const base = pattern * 4 * bar;
    const accentOffset = tpb;
    const accentNote = accentNotes[pattern % accentNotes.length];
    const accentVelocity = 96 - pattern;
    for (let barIndex = 0; barIndex < 4; barIndex++) {
      const onset = base + barIndex * bar;
      noteEvents.push(
        {
          tick: onset,
          event: {
            type: "noteOn",
            channel: 9,
            noteNumber: 36,
            velocity: 100,
          },
        },
        {
          tick: onset + 120,
          event: {
            type: "noteOff",
            channel: 9,
            noteNumber: 36,
            velocity: 0,
          },
        },
        {
          tick: onset + accentOffset,
          event: {
            type: "noteOn",
            channel: 9,
            noteNumber: accentNote,
            velocity: accentVelocity,
          },
        },
        {
          tick: onset + accentOffset + 120,
          event: {
            type: "noteOff",
            channel: 9,
            noteNumber: accentNote,
            velocity: 0,
          },
        },
      );
    }
  }

  const data: MidiData = {
    header: { format: 1, numTracks: 2, ticksPerBeat: tpb },
    tracks: [
      [
        {
          deltaTime: 0,
          type: "setTempo",
          meta: true,
          microsecondsPerBeat: Math.round(60_000_000 / 120),
        },
        { deltaTime: 0, type: "endOfTrack", meta: true },
      ],
      [
        ...makeTrackFromAbsolute(noteEvents),
        { deltaTime: 0, type: "endOfTrack", meta: true },
      ],
    ],
  };
  return new Uint8Array(writeMidi(data));
}

function manyMelodicTracksMidi(trackCount: number): Uint8Array {
  const tpb = 480;
  const bar = tpb * 4;
  const tracks: MidiEvent[][] = [
    [
      {
        deltaTime: 0,
        type: "setTempo",
        meta: true,
        microsecondsPerBeat: Math.round(60_000_000 / 112),
      },
      { deltaTime: 0, type: "endOfTrack", meta: true },
    ],
  ];

  for (let trackIndex = 0; trackIndex < trackCount; trackIndex++) {
    const pitch = 48 + trackIndex;
    const noteEvents: Array<{
      tick: number;
      event: Omit<MidiEvent, "deltaTime">;
    }> = [
      {
        tick: 0,
        event: {
          type: "trackName",
          meta: true,
          text: `Source ${trackIndex + 1}`,
        },
      },
    ];

    for (let barIndex = 0; barIndex < 8; barIndex++) {
      const onset = barIndex * bar;
      noteEvents.push(
        {
          tick: onset,
          event: {
            type: "noteOn",
            channel: trackIndex % 8,
            noteNumber: pitch,
            velocity: 82,
          },
        },
        {
          tick: onset + tpb,
          event: {
            type: "noteOff",
            channel: trackIndex % 8,
            noteNumber: pitch,
            velocity: 0,
          },
        },
      );
    }

    tracks.push([
      ...makeTrackFromAbsolute(noteEvents),
      { deltaTime: 0, type: "endOfTrack", meta: true },
    ]);
  }

  const data: MidiData = {
    header: { format: 1, numTracks: tracks.length, ticksPerBeat: tpb },
    tracks,
  };
  return new Uint8Array(writeMidi(data));
}

function manyLongDistinctTracksMidi(
  trackCount: number,
  patternCount = 10,
): Uint8Array {
  const tpb = 480;
  const bar = tpb * 4;
  const tracks: MidiEvent[][] = [
    [
      {
        deltaTime: 0,
        type: "setTempo",
        meta: true,
        microsecondsPerBeat: Math.round(60_000_000 / 120),
      },
      { deltaTime: 0, type: "endOfTrack", meta: true },
    ],
  ];

  for (let trackIndex = 0; trackIndex < trackCount; trackIndex++) {
    const noteEvents: Array<{
      tick: number;
      event: Omit<MidiEvent, "deltaTime">;
    }> = [
      {
        tick: 0,
        event: {
          type: "trackName",
          meta: true,
          text: `Long ${trackIndex + 1}`,
        },
      },
    ];

    for (let pattern = 0; pattern < patternCount; pattern++) {
      const pitch = 48 + trackIndex * 5 + pattern;
      for (let barIndex = 0; barIndex < 4; barIndex++) {
        const onset = (pattern * 4 + barIndex) * bar;
        noteEvents.push(
          {
            tick: onset,
            event: {
              type: "noteOn",
              channel: trackIndex,
              noteNumber: pitch,
              velocity: 88,
            },
          },
          {
            tick: onset + tpb,
            event: {
              type: "noteOff",
              channel: trackIndex,
              noteNumber: pitch,
              velocity: 0,
            },
          },
        );
      }
    }

    tracks.push([
      ...makeTrackFromAbsolute(noteEvents),
      { deltaTime: 0, type: "endOfTrack", meta: true },
    ]);
  }

  const data: MidiData = {
    header: { format: 1, numTracks: tracks.length, ticksPerBeat: tpb },
    tracks,
  };
  return new Uint8Array(writeMidi(data));
}

describe("MIDI new-project importer", () => {
  it("authors a one-bar MIDI as a 16-step pattern without trailing silence", () => {
    const baseline = new Uint8Array(readFileSync(BASELINE));
    const result = buildMidiProjectFromBytes(
      oneBarDrumMidi(),
      "amen-break.mid",
      baseline,
    );

    expect(result.summary).toMatchObject({
      patterns: 1,
      scenes: 1,
      totalBars: 1,
      sourceTotalBars: 1,
      sourceTotal16ths: 16,
      rangeStart16ths: 0,
      rangeEnd16ths: 16,
    });
    expect(result.summary.trackSelection?.total16ths).toBe(16);
    expect(result.project.tracks[0].patterns[0].totalSteps).toBe(16);
    expect(result.project.scenes[0].length16ths).toBe(16);
    expect(result.project.songs[0].sceneChain).toEqual([0]);
  });

  it("reuses a repeated chord pattern across Song scenes without duplicating a second chord slot", () => {
    const baseline = new Uint8Array(readFileSync(BASELINE));
    const result = buildMidiProjectFromBytes(
      singlePolyphonicLaneMidi(),
      "single-chord.mid",
      baseline,
      {
        bpmOverride: 101.5,
      },
    );

    expect(result.summary).toMatchObject({
      bpm: expect.closeTo(101.5, 0.01),
      patterns: 2,
      totalBars: 8,
      activeTracks: [7],
    });
    expect(result.summary.notesPerPatternByTrack[7]).toEqual([24, 24]);
    expect(result.summary.notesPerPatternByTrack[8]).toBeUndefined();
    expect(result.project.fileName).toBe("singlechord.xy");
    expect(result.project.modified).toBe(true);
    expect(result.project.tempoBpm).toBeCloseTo(101.5, 1);
    expect(result.project.tracks[6].patterns).toHaveLength(1);
    expect(result.project.tracks[6].patterns[0].notes).toHaveLength(24);
    expect(result.project.songs[0].sceneChain).toEqual([0, 1]);
  });

  it("keeps all long-MIDI scenes by banking a seventeenth unique pattern on a spare track", () => {
    const baseline = new Uint8Array(readFileSync(BASELINE));
    const result = buildMidiProjectFromBytes(
      longDistinctDrumMidi(),
      "long-drums.mid",
      baseline,
    );

    expect(result.summary).toMatchObject({
      patterns: 17,
      totalBars: 68,
      importedNotes: 136,
      activeTracks: [1, 2],
    });
    expect(result.summary.notesPerPatternByTrack[1]).toHaveLength(17);
    expect(result.project.tracks[0].patterns).toHaveLength(16);
    expect(result.project.tracks[1].patterns).toHaveLength(1);
    expect(result.project.songs[0].sceneChain).toEqual(
      Array.from({ length: 17 }, (_, index) => index),
    );

    for (let sceneIndex = 0; sceneIndex < 16; sceneIndex++) {
      const scene = result.project.scenes[sceneIndex];
      expect(scene.present).toBe(true);
      expect(scene.patternByTrack.slice(0, 2)).toEqual([sceneIndex, 0]);
      expect(scene.mutedTracks.slice(0, 2)).toEqual([false, true]);
    }
    expect(result.project.scenes[16].present).toBe(true);
    expect(result.project.scenes[16].patternByTrack.slice(0, 2)).toEqual([
      0, 0,
    ]);
    expect(result.project.scenes[16].mutedTracks.slice(0, 2)).toEqual([
      true,
      false,
    ]);
  });

  it("constrains over-capacity MIDI files with selectable source lanes", () => {
    const baseline = new Uint8Array(readFileSync(BASELINE));
    const midi = manyMelodicTracksMidi(10);
    const result = buildMidiProjectFromBytes(midi, "many.mid", baseline);

    expect(result.summary.trackSelection).toMatchObject({
      isSelectionRecommended: true,
      requiredBankCount: 10,
      selectedBankCount: 8,
      totalBars: 8,
      total16ths: 128,
    });
    expect(result.summary.trackSelection?.tracks).toHaveLength(10);
    expect(result.summary.trackSelection?.tracks[0]).toMatchObject({
      name: "Source 1",
      noteCount: 8,
      bankCount: 1,
    });
    expect(result.summary.trackSelection?.selectedTrackIds).toHaveLength(8);
    expect(result.summary.activeTracks).toHaveLength(8);
  });

  it("uses explicit selected MIDI source lanes for project generation", () => {
    const baseline = new Uint8Array(readFileSync(BASELINE));
    const midi = manyMelodicTracksMidi(10);
    const result = buildMidiProjectFromBytes(midi, "many.mid", baseline, {
      selectedTrackIds: ["2:1", "4:3"],
    });

    expect(result.summary.trackSelection?.selectedTrackIds).toEqual([
      "2:1",
      "4:3",
    ]);
    expect(result.summary.trackSelection?.selectedBankCount).toBe(2);
    expect(result.summary.activeTracks).toHaveLength(2);
    expect(result.summary.importedNotes).toBe(16);
  });

  it("can fit an over-bank selection by shortening the MIDI range", () => {
    const baseline = new Uint8Array(readFileSync(BASELINE));
    const midi = manyLongDistinctTracksMidi(5, 17);
    const result = buildMidiProjectFromBytes(midi, "long-many.mid", baseline, {
      selectedTrackIds: ["1:0", "2:1", "3:2", "4:3", "5:4"],
      fitToCapacity: true,
    });

    expect(result.summary.rangeWasAutoFit).toBe(true);
    expect(result.summary.totalBars).toBe(64);
    expect(result.summary.sourceTotalBars).toBe(68);
    expect(result.summary.trackSelection?.selectedBankCount).toBe(5);
    expect(result.summary.activeTracks).toHaveLength(5);
  });

  it("shortens MIDI-derived project filenames for OP-XY projects", () => {
    const baseline = new Uint8Array(readFileSync(BASELINE));
    const midi = singlePolyphonicLaneMidi();

    expect(
      buildMidiProjectFromBytes(
        midi,
        "Deep Purple - Child In Time (Gennaro Marchese).mid",
        baseline,
      ).project.fileName,
    ).toBe("childintime.xy");
    expect(
      buildMidiProjectFromBytes(
        midi,
        "Phil Collins - In The Air Tonight (Music Sales Ltd.).mid",
        baseline,
      ).project.fileName,
    ).toBe("intheairtonight.xy");
    expect(
      buildMidiProjectFromBytes(
        midi,
        "01 - Artist - A Very Long Song Title.mid",
        baseline,
      ).project.fileName,
    ).toBe("averylongsongtit.xy");
  });
});
