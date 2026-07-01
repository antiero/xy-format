export const GM_DRUM_MIDI_CHANNEL = 9;

const OP_XY_TO_GM_DRUM_NOTE: Record<number, number> = {
  53: 36,
  56: 38,
  57: 37,
  61: 42,
  62: 39,
  63: 46,
  69: 50,
  67: 47,
  65: 45,
  49: 49,
  60: 70,
  70: 39,
};

export function isDrumTrackIndex(trackIndex: number): boolean {
  return trackIndex === 0 || trackIndex === 1;
}

export function gmDrumNote(note: number): number {
  return OP_XY_TO_GM_DRUM_NOTE[note] ?? note;
}

export function outputMidiChannelForTrack(trackIndex: number): number {
  return isDrumTrackIndex(trackIndex) ? GM_DRUM_MIDI_CHANNEL : trackIndex;
}

export function outputMidiNoteForTrack(
  trackIndex: number,
  note: number,
): number {
  return isDrumTrackIndex(trackIndex) ? gmDrumNote(note) : note;
}
