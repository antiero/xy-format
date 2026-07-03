import type { MidiTrackSelectionSummary } from "./midiImporter";

type MidiEditorTrackSelection = Pick<
  MidiTrackSelectionSummary,
  | "isSelectionRecommended"
  | "rangeStart16ths"
  | "rangeEnd16ths"
  | "sourceTotal16ths"
  | "tracks"
  | "maxInstrumentTracks"
>;

export function midiImportNeedsEditor(
  summary: { trackSelection: MidiEditorTrackSelection | null } | null,
): boolean {
  const selection = summary?.trackSelection;
  return (
    !!selection &&
    (selection.isSelectionRecommended ||
      selection.rangeStart16ths > 0 ||
      selection.rangeEnd16ths < selection.sourceTotal16ths ||
      selection.tracks.length > selection.maxInstrumentTracks)
  );
}
