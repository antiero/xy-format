export type ProjectNoteCountSource = {
  tracks: Array<{
    patterns: Array<{
      notes: readonly unknown[];
    }>;
  }>;
};

export type MidiImportNoteCountSource = {
  importedNotes: number;
};

export function projectNoteCount(
  project: ProjectNoteCountSource | null | undefined,
): number {
  if (!project) return 0;

  return project.tracks.reduce(
    (projectTotal, track) =>
      projectTotal +
      track.patterns.reduce(
        (trackTotal, pattern) => trackTotal + pattern.notes.length,
        0,
      ),
    0,
  );
}

export function midiImportNoteCount(
  summary: MidiImportNoteCountSource | null | undefined,
): number {
  const count = Number(summary?.importedNotes);
  if (!Number.isFinite(count) || count <= 0) return 0;

  return Math.floor(count);
}
