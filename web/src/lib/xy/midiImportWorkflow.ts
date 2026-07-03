import type {
  MidiTrackSelectionOption,
  MidiTrackSelectionSummary,
} from "./midiImporter";

type MidiEditorTrackSelection = Pick<
  MidiTrackSelectionSummary,
  | "isSelectionRecommended"
  | "rangeStart16ths"
  | "rangeEnd16ths"
  | "sourceTotal16ths"
  | "maxInstrumentTracks"
> & {
  tracks: Array<Pick<MidiTrackSelectionOption, "isDrum">>;
};

export function midiImportNeedsEditor(
  summary: { trackSelection: MidiEditorTrackSelection | null } | null,
): boolean {
  const selection = summary?.trackSelection;
  return (
    !!selection &&
    (selection.isSelectionRecommended ||
      selection.tracks.some((track) => track.isDrum) ||
      selection.rangeStart16ths > 0 ||
      selection.rangeEnd16ths < selection.sourceTotal16ths ||
      selection.tracks.length > selection.maxInstrumentTracks)
  );
}
