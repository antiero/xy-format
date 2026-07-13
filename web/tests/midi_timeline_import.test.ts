import { readFileSync } from "fs";
import { describe, expect, it } from "vitest";
import { parseMidi, writeMidi, type MidiData, type MidiEvent } from "midi-file";
import { buildMidiProjectFromBytes } from "../src/lib/xy/midiImporter";
import {
  buildMidiPatternWindows,
  buildMidiTimeline,
} from "../src/lib/xy/midiTimeline";

const BASELINE = "../src/one-off-changes-from-default/unnamed 1.xy";

function trackFromAbsolute(
  events: Array<{ tick: number; event: Omit<MidiEvent, "deltaTime"> }>,
): MidiEvent[] {
  const sorted = [...events].sort(
    (a, b) => a.tick - b.tick || (a.event.type === "noteOff" ? -1 : 1),
  );
  let previousTick = 0;
  return sorted.map(({ tick, event }) => {
    const deltaTime = tick - previousTick;
    previousTick = tick;
    return { ...event, deltaTime } as MidiEvent;
  });
}

function goldenBrownTimingMidi(): Uint8Array {
  const ticksPerBeat = 384;
  const events: Array<{
    tick: number;
    event: Omit<MidiEvent, "deltaTime">;
  }> = [
    {
      tick: 0,
      event: {
        type: "setTempo",
        meta: true,
        microsecondsPerBeat: 300_000,
      },
    },
    {
      tick: 0,
      event: {
        type: "timeSignature",
        meta: true,
        numerator: 3,
        denominator: 4,
        metronome: 24,
        thirtyseconds: 8,
      },
    },
    {
      tick: 2304,
      event: {
        type: "setTempo",
        meta: true,
        microsecondsPerBeat: Math.round(60_000_000 / 190),
      },
    },
    {
      tick: 8064,
      event: {
        type: "timeSignature",
        meta: true,
        numerator: 4,
        denominator: 4,
        metronome: 24,
        thirtyseconds: 8,
      },
    },
    {
      tick: 9600,
      event: {
        type: "timeSignature",
        meta: true,
        numerator: 3,
        denominator: 4,
        metronome: 24,
        thirtyseconds: 8,
      },
    },
  ];

  const noteStarts = [4608, 4832, 5760, 6912, 8064, 9600, 10752, 11904, 13056];
  noteStarts.forEach((tick, index) => {
    const gate = tick === 13056 ? 384 : 192;
    events.push(
      {
        tick,
        event: {
          type: "noteOn",
          channel: 0,
          noteNumber: 60 + index,
          velocity: 88,
        },
      },
      {
        tick: tick + gate,
        event: {
          type: "noteOff",
          channel: 0,
          noteNumber: 60 + index,
          velocity: 0,
        },
      },
    );
  });

  const data: MidiData = {
    header: { format: 0, numTracks: 1, ticksPerBeat },
    tracks: [
      [
        ...trackFromAbsolute(events),
        { deltaTime: 0, type: "endOfTrack", meta: true },
      ],
    ],
  };
  return new Uint8Array(writeMidi(data));
}

function constantMeterMidi(numerator: number, denominator: number): Uint8Array {
  const ticksPerBeat = 384;
  const events: Array<{
    tick: number;
    event: Omit<MidiEvent, "deltaTime">;
  }> = [
    {
      tick: 0,
      event: {
        type: "timeSignature",
        meta: true,
        numerator,
        denominator,
        metronome: 24,
        thirtyseconds: 8,
      },
    },
  ];
  [0, 384, 768, 1152].forEach((tick, index) => {
    events.push(
      {
        tick,
        event: {
          type: "noteOn",
          channel: 0,
          noteNumber: 60 + index,
          velocity: 88,
        },
      },
      {
        tick: tick + 192,
        event: {
          type: "noteOff",
          channel: 0,
          noteNumber: 60 + index,
          velocity: 0,
        },
      },
    );
  });

  return new Uint8Array(
    writeMidi({
      header: { format: 0, numTracks: 1, ticksPerBeat },
      tracks: [
        [
          ...trackFromAbsolute(events),
          { deltaTime: 0, type: "endOfTrack", meta: true },
        ],
      ],
    }),
  );
}

describe("variable MIDI timeline import", () => {
  it("groups four musical bars and bakes tempo changes into pattern timing", () => {
    const midi = parseMidi(goldenBrownTimingMidi());
    const timeline = buildMidiTimeline(midi, {
      contentStartTick: 4608,
      contentEndTick: 13440,
    });
    const windows = buildMidiPatternWindows(
      timeline,
      0,
      timeline.sourceTotal16ths,
      96,
    );

    expect(timeline.projectBpm).toBe(190);
    expect(timeline.sourceTotalBars).toBe(12);
    expect(timeline.sourceTotal16ths).toBe(148);
    expect(windows.map((window) => window.barCount)).toEqual([4, 4, 4]);
    expect(windows.map((window) => window.steps)).toEqual([47, 52, 48]);
    expect(windows.map((window) => window.sourceEnd16ths)).toEqual([
      48, 100, 148,
    ]);

    const overriddenTimeline = buildMidiTimeline(midi, {
      contentStartTick: 4608,
      contentEndTick: 13440,
      bpmOverride: 200,
    });
    expect(overriddenTimeline.projectBpm).toBe(200);
    expect(
      buildMidiPatternWindows(
        overriddenTimeline,
        0,
        overriddenTimeline.sourceTotal16ths,
        96,
      ).map((window) => window.steps),
    ).toEqual([48, 52, 48]);
  });

  it("authors variable-length scenes at the tempo active when the music begins", () => {
    const result = buildMidiProjectFromBytes(
      goldenBrownTimingMidi(),
      "mixed-meter.mid",
      new Uint8Array(readFileSync(BASELINE)),
    );

    expect(result.summary).toMatchObject({
      bpm: 190,
      tempoChanges: 2,
      timeSignatureChanges: 3,
      patterns: 3,
      scenes: 3,
      totalBars: 12,
      sourceTotalBars: 12,
      sourceTotal16ths: 148,
      importedNotes: 9,
    });
    expect(result.project.imageProject.getSceneLengthMode()).toBe(0);
    expect(result.project.imageProject.getTimeSignatureRaw()).toBe(0x10);
    expect(
      result.project.scenes.slice(0, 3).map((scene) => scene.length16ths),
    ).toEqual([47, 52, 48]);
    const sourceTrackIndex = (result.summary.activeTracks[0] ?? 1) - 1;
    expect(result.project.scenes[0].mutedTracks[sourceTrackIndex]).toBe(true);
    expect(result.project.scenes[1].mutedTracks[sourceTrackIndex]).toBe(false);

    const importedNotes = result.project.tracks.flatMap((track) =>
      track.patterns.flatMap((pattern) => pattern.notes),
    );
    const offGridNote = importedNotes.find((note) => note.note === 61);
    expect(offGridNote?.start16ths).toBeCloseTo(1120 / 480, 4);
    expect(offGridNote?.duration16ths).toBeCloseTo(2, 4);

    const playbackSeconds =
      result.project.scenes
        .slice(0, 3)
        .reduce((sum, scene) => sum + scene.length16ths, 0) *
      (15 / result.summary.bpm);
    const sourceSeconds = 6 * (60 / 200) + 31 * (60 / 190);
    expect(Math.abs(playbackSeconds - sourceSeconds)).toBeLessThan(0.02);
  });

  it("writes a supported constant MIDI meter to the project header", () => {
    const result = buildMidiProjectFromBytes(
      constantMeterMidi(6, 8),
      "six-eight.mid",
      new Uint8Array(readFileSync(BASELINE)),
    );

    expect(result.project.imageProject.getSceneLengthMode()).toBe(0);
    expect(result.project.imageProject.getTimeSignatureRaw()).toBe(0x13);
  });
});
