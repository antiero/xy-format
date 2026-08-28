const DEFAULT_TOP_PITCH = 84;
const DEFAULT_BOTTOM_PITCH = 36;
const MIDI_MIN = 0;
const MIDI_MAX = 127;
const EXPANDED_PADDING = 5;

export type PianoRollPitchMode = "expanded" | "used";

export function expandedPianoRollPitches(pitches: number[]): number[] {
  if (pitches.length === 0) {
    return descendingRange(DEFAULT_TOP_PITCH, DEFAULT_BOTTOM_PITCH);
  }

  const highest = Math.min(MIDI_MAX, Math.max(...pitches) + EXPANDED_PADDING);
  const lowest = Math.max(MIDI_MIN, Math.min(...pitches) - EXPANDED_PADDING);
  return descendingRange(highest, lowest);
}

export function usedPianoRollPitches(pitches: number[]): number[] {
  return [...new Set(pitches)].sort((left, right) => right - left);
}

export function visiblePianoRollPitches(
  pitches: number[],
  mode: PianoRollPitchMode,
): number[] {
  const used = usedPianoRollPitches(pitches);
  return mode === "used" && used.length > 0
    ? used
    : expandedPianoRollPitches(pitches);
}

export function collapsedRowIndex(
  pitch: number,
  visiblePitches: number[],
): number {
  const visibleIndex = visiblePitches.indexOf(pitch);
  if (visibleIndex >= 0) return visibleIndex;
  return visiblePitches.filter((visiblePitch) => visiblePitch > pitch).length;
}

export function movePitchByVisibleRows(
  pitch: number,
  deltaRows: number,
  visiblePitches: number[],
): number {
  if (visiblePitches.length === 0) return pitch;
  const startIndex = visiblePitches.indexOf(pitch);
  if (startIndex < 0) return pitch;
  const targetIndex = Math.max(
    0,
    Math.min(visiblePitches.length - 1, startIndex + deltaRows),
  );
  return visiblePitches[targetIndex];
}

function descendingRange(highest: number, lowest: number): number[] {
  return Array.from({ length: highest - lowest + 1 }, (_, index) => {
    return highest - index;
  });
}
