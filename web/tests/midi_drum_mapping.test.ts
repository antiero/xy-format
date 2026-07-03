import { readFileSync } from "fs";
import { writeMidi, type MidiData, type MidiEvent } from "midi-file";
import { describe, expect, it } from "vitest";
import {
  buildMidiProjectFromBytes,
  type MidiImportOptions,
} from "../src/lib/xy/midiImporter";

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

function channel10DrumMidi(notes: number[]): Uint8Array {
  const tpb = 480;
  const events: Array<{ tick: number; event: Omit<MidiEvent, "deltaTime"> }> =
    [];

  notes.forEach((noteNumber, index) => {
    const tick = index * 120;
    events.push(
      {
        tick,
        event: { type: "noteOn", channel: 9, noteNumber, velocity: 108 },
      },
      {
        tick: tick + 60,
        event: { type: "noteOff", channel: 9, noteNumber, velocity: 0 },
      },
    );
  });

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
        ...makeTrackFromAbsolute(events),
        { deltaTime: 0, type: "endOfTrack", meta: true },
      ],
    ],
  };
  return new Uint8Array(writeMidi(data));
}

function importedDrumNotes(
  gmNotes: number[],
  options: MidiImportOptions = {},
): number[] {
  const baseline = new Uint8Array(readFileSync(BASELINE));
  const result = buildMidiProjectFromBytes(
    channel10DrumMidi(gmNotes),
    "drums.mid",
    baseline,
    options,
  );
  return result.project.tracks[0].patterns[0].notes.map((note) => note.note);
}

describe("MIDI GM drum mapping", () => {
  it("maps channel 10 GM drums to the OP-XY percussion map by default", () => {
    const result = importedDrumNotes([
      35, 36, 37, 38, 39, 40, 42, 44, 45, 46, 47, 49, 50, 56, 70,
    ]);

    expect(result).toEqual([
      53, 53, 57, 56, 62, 56, 61, 61, 65, 63, 67, 49, 69, 56, 60,
    ]);
  });

  it("can leave channel 10 drum note numbers unchanged", () => {
    const result = importedDrumNotes([36, 38, 42, 46, 70], {
      mapGmDrums: false,
    });

    expect(result).toEqual([36, 38, 42, 46, 70]);
  });

  it("reports the active drum-map mode in the import summary", () => {
    const baseline = new Uint8Array(readFileSync(BASELINE));
    const result = buildMidiProjectFromBytes(
      channel10DrumMidi([36, 38, 42]),
      "drums.mid",
      baseline,
    );

    expect(result.summary.mapGmDrums).toBe(true);
    expect(result.summary.trackSelection?.tracks[0].previewNotes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ note: 53 }),
        expect.objectContaining({ note: 56 }),
        expect.objectContaining({ note: 61 }),
      ]),
    );
  });
});
