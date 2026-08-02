import type { MidiData, MidiEvent } from "midi-file";

export type MidiProgramSelection = {
  programNumber: number;
  programName: string;
  bankMSB: number;
  bankLSB: number;
};

type AbsoluteChannelEvent = {
  tick: number;
  trackIndex: number;
  eventIndex: number;
  event: MidiEvent;
};

export const GM_PROGRAM_NAMES = [
  "Acoustic Grand Piano",
  "Bright Acoustic Piano",
  "Electric Grand Piano",
  "Honky-tonk Piano",
  "Electric Piano 1",
  "Electric Piano 2",
  "Harpsichord",
  "Clavinet",
  "Celesta",
  "Glockenspiel",
  "Music Box",
  "Vibraphone",
  "Marimba",
  "Xylophone",
  "Tubular Bells",
  "Dulcimer",
  "Drawbar Organ",
  "Percussive Organ",
  "Rock Organ",
  "Church Organ",
  "Reed Organ",
  "Accordion",
  "Harmonica",
  "Tango Accordion",
  "Acoustic Guitar (nylon)",
  "Acoustic Guitar (steel)",
  "Electric Guitar (jazz)",
  "Electric Guitar (clean)",
  "Electric Guitar (muted)",
  "Overdriven Guitar",
  "Distortion Guitar",
  "Guitar Harmonics",
  "Acoustic Bass",
  "Electric Bass (finger)",
  "Electric Bass (pick)",
  "Fretless Bass",
  "Slap Bass 1",
  "Slap Bass 2",
  "Synth Bass 1",
  "Synth Bass 2",
  "Violin",
  "Viola",
  "Cello",
  "Contrabass",
  "Tremolo Strings",
  "Pizzicato Strings",
  "Orchestral Harp",
  "Timpani",
  "String Ensemble 1",
  "String Ensemble 2",
  "Synth Strings 1",
  "Synth Strings 2",
  "Choir Aahs",
  "Voice Oohs",
  "Synth Voice",
  "Orchestra Hit",
  "Trumpet",
  "Trombone",
  "Tuba",
  "Muted Trumpet",
  "French Horn",
  "Brass Section",
  "Synth Brass 1",
  "Synth Brass 2",
  "Soprano Sax",
  "Alto Sax",
  "Tenor Sax",
  "Baritone Sax",
  "Oboe",
  "English Horn",
  "Bassoon",
  "Clarinet",
  "Piccolo",
  "Flute",
  "Recorder",
  "Pan Flute",
  "Blown Bottle",
  "Shakuhachi",
  "Whistle",
  "Ocarina",
  "Lead 1 (square)",
  "Lead 2 (sawtooth)",
  "Lead 3 (calliope)",
  "Lead 4 (chiff)",
  "Lead 5 (charang)",
  "Lead 6 (voice)",
  "Lead 7 (fifths)",
  "Lead 8 (bass + lead)",
  "Pad 1 (new age)",
  "Pad 2 (warm)",
  "Pad 3 (polysynth)",
  "Pad 4 (choir)",
  "Pad 5 (bowed)",
  "Pad 6 (metallic)",
  "Pad 7 (halo)",
  "Pad 8 (sweep)",
  "FX 1 (rain)",
  "FX 2 (soundtrack)",
  "FX 3 (crystal)",
  "FX 4 (atmosphere)",
  "FX 5 (brightness)",
  "FX 6 (goblins)",
  "FX 7 (echoes)",
  "FX 8 (sci-fi)",
  "Sitar",
  "Banjo",
  "Shamisen",
  "Koto",
  "Kalimba",
  "Bag Pipe",
  "Fiddle",
  "Shanai",
  "Tinkle Bell",
  "Agogo",
  "Steel Drums",
  "Woodblock",
  "Taiko Drum",
  "Melodic Tom",
  "Synth Drum",
  "Reverse Cymbal",
  "Guitar Fret Noise",
  "Breath Noise",
  "Seashore",
  "Bird Tweet",
  "Telephone Ring",
  "Helicopter",
  "Applause",
  "Gunshot",
] as const;

export function gmProgramName(programNumber: number): string {
  return GM_PROGRAM_NAMES[programNumber] ?? `Program ${programNumber + 1}`;
}

export function collectMidiProgramTimeline(
  midi: MidiData,
): Map<number, Array<{ tick: number; selection: MidiProgramSelection }>> {
  const events: AbsoluteChannelEvent[] = [];

  midi.tracks.forEach((track, trackIndex) => {
    let tick = 0;
    track.forEach((event, eventIndex) => {
      tick += event.deltaTime;
      if (
        event.type === "programChange" ||
        (event.type === "controller" &&
          (event.controllerType === 0 || event.controllerType === 32))
      ) {
        events.push({ tick, trackIndex, eventIndex, event });
      }
    });
  });

  events.sort(
    (a, b) =>
      a.tick - b.tick ||
      a.trackIndex - b.trackIndex ||
      a.eventIndex - b.eventIndex,
  );

  const bankMSB = new Array<number>(16).fill(0);
  const bankLSB = new Array<number>(16).fill(0);
  const timeline = new Map<
    number,
    Array<{ tick: number; selection: MidiProgramSelection }>
  >();

  for (const item of events) {
    const event = item.event;
    if (event.type === "controller") {
      if (event.controllerType === 0) bankMSB[event.channel] = event.value;
      if (event.controllerType === 32) bankLSB[event.channel] = event.value;
      continue;
    }
    if (event.type !== "programChange") continue;
    const changes = timeline.get(event.channel) ?? [];
    changes.push({
      tick: item.tick,
      selection: {
        programNumber: event.programNumber,
        programName: gmProgramName(event.programNumber),
        bankMSB: bankMSB[event.channel],
        bankLSB: bankLSB[event.channel],
      },
    });
    timeline.set(event.channel, changes);
  }

  return timeline;
}

export function midiProgramAtTick(
  timeline: Map<
    number,
    Array<{ tick: number; selection: MidiProgramSelection }>
  >,
  channel: number,
  tick: number,
): MidiProgramSelection {
  const changes = timeline.get(channel) ?? [];
  let selected: MidiProgramSelection = {
    programNumber: 0,
    programName: gmProgramName(0),
    bankMSB: 0,
    bankLSB: 0,
  };
  for (const change of changes) {
    if (change.tick > tick) break;
    selected = change.selection;
  }
  return selected;
}
