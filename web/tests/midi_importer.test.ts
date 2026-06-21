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

describe("MIDI new-project importer", () => {
  it("segments a single polyphonic lane into chord-track patterns without duplicating a second chord slot", () => {
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
    expect(result.project.fileName).toBe("single-chord.xy");
    expect(result.project.modified).toBe(true);
    expect(result.project.tempoBpm).toBeCloseTo(101.5, 1);
    expect(result.project.tracks[6].patterns).toHaveLength(2);
    expect(result.project.tracks[6].patterns[0].notes).toHaveLength(24);
    expect(result.project.songs[0].sceneChain).toEqual([0, 1]);
  });
});
