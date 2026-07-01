import { TRACK_COUNT } from "./image_writer";
import type {
  XYPatternViewModel,
  XYProjectViewModel,
  XYSceneViewModel,
  XYTrackViewModel,
} from "./projectViewModel";

export const ARRANGER_TRACK_COUNT = 8;
export const ARRANGER_PATTERN_ROWS = 9;
export const ARRANGER_CENTER_ROW = 4;
export const ARRANGER_MAX_PATTERNS = 9;

export type ArrangerSequenceSource = "song" | "scenes";

export type ArrangerSequenceStep = {
  index: number;
  sceneIndex: number;
  label: string;
};

export type ArrangerSequence = {
  source: ArrangerSequenceSource;
  sceneIndexes: number[];
  steps: ArrangerSequenceStep[];
};

export type ArrangerNoteDot = {
  id: string;
  leftPct: number;
  topPct: number;
};

export type ArrangerPatternSlot = {
  row: number;
  patternIndex: number | null;
  label: string;
  active: boolean;
  muted: boolean;
  exists: boolean;
  noteCount: number;
  notes: ArrangerNoteDot[];
};

export type ArrangerTrackColumn = {
  trackIndex: number;
  label: string;
  muted: boolean;
  activePatternIndex: number;
  slots: ArrangerPatternSlot[];
};

export type ArrangerFrame = {
  sequence: ArrangerSequence;
  selectedStepIndex: number;
  scene: XYSceneViewModel;
  columns: ArrangerTrackColumn[];
};

function validSceneIndex(
  project: XYProjectViewModel,
  sceneIndex: number,
): boolean {
  return sceneIndex >= 0 && sceneIndex < project.scenes.length;
}

function sequenceLabel(source: ArrangerSequenceSource, index: number): string {
  return source === "song" ? `${index + 1}` : `${index + 1}`;
}

export function buildArrangerSequence(
  project: XYProjectViewModel,
): ArrangerSequence {
  const song = project.songs[0];
  const songSceneIndexes =
    song?.supported && song.sceneChain.length > 0
      ? song.sceneChain.filter((sceneIndex) =>
          validSceneIndex(project, sceneIndex),
        )
      : [];

  const source: ArrangerSequenceSource =
    songSceneIndexes.length > 0 ? "song" : "scenes";
  const sceneIndexes =
    songSceneIndexes.length > 0
      ? songSceneIndexes
      : project.scenes
          .filter((scene) => scene.present)
          .map((scene) => scene.index);
  const fallbackSceneIndexes =
    sceneIndexes.length > 0
      ? sceneIndexes
      : [
          Math.max(
            0,
            Math.min(project.scenes.length - 1, project.activeSceneIndex),
          ),
        ];

  return {
    source,
    sceneIndexes: fallbackSceneIndexes,
    steps: fallbackSceneIndexes.map((sceneIndex, index) => ({
      index,
      sceneIndex,
      label: sequenceLabel(source, index),
    })),
  };
}

function clampPatternIndex(
  track: XYTrackViewModel,
  patternIndex: number,
): number {
  return Math.max(
    0,
    Math.min(
      ARRANGER_MAX_PATTERNS - 1,
      Math.min(Math.max(0, track.patterns.length - 1), patternIndex || 0),
    ),
  );
}

function patternNoteDots(
  pattern: XYPatternViewModel | undefined,
): ArrangerNoteDot[] {
  if (!pattern || pattern.notes.length === 0) return [];

  const visibleNotes = pattern.notes.slice(0, 28);
  const minNote = Math.min(...visibleNotes.map((note) => note.note));
  const maxNote = Math.max(...visibleNotes.map((note) => note.note));
  const pitchSpan = Math.max(1, maxNote - minNote);
  const length = Math.max(1, pattern.effectiveLength16ths);

  return visibleNotes.map((note) => ({
    id: note.id,
    leftPct: Math.max(3, Math.min(96, (note.start16ths / length) * 100)),
    topPct: Math.max(
      12,
      Math.min(82, 82 - ((note.note - minNote) / pitchSpan) * 70),
    ),
  }));
}

function buildColumn(
  track: XYTrackViewModel,
  scene: XYSceneViewModel,
): ArrangerTrackColumn {
  const activePatternIndex = clampPatternIndex(
    track,
    scene.patternByTrack[track.index] ?? 0,
  );
  const muted = scene.mutedTracks[track.index] ?? false;

  const slots = Array.from({ length: ARRANGER_PATTERN_ROWS }, (_, row) => {
    const patternIndex = activePatternIndex + row - ARRANGER_CENTER_ROW;
    const pattern =
      patternIndex >= 0 && patternIndex < ARRANGER_MAX_PATTERNS
        ? track.patterns[patternIndex]
        : undefined;

    return {
      row,
      patternIndex:
        patternIndex >= 0 && patternIndex < ARRANGER_MAX_PATTERNS
          ? patternIndex
          : null,
      label:
        patternIndex >= 0 && patternIndex < ARRANGER_MAX_PATTERNS
          ? `${patternIndex + 1}`
          : "",
      active: row === ARRANGER_CENTER_ROW,
      muted,
      exists: Boolean(pattern),
      noteCount: pattern?.notes.length ?? 0,
      notes: patternNoteDots(pattern),
    };
  });

  return {
    trackIndex: track.index,
    label: String(track.index + 1),
    muted,
    activePatternIndex,
    slots,
  };
}

export function buildArrangerFrame(
  project: XYProjectViewModel,
  selectedStepIndex = 0,
): ArrangerFrame {
  const sequence = buildArrangerSequence(project);
  const clampedStepIndex = Math.max(
    0,
    Math.min(sequence.steps.length - 1, selectedStepIndex),
  );
  const sceneIndex =
    sequence.steps[clampedStepIndex]?.sceneIndex ?? project.activeSceneIndex;
  const scene = project.scenes[sceneIndex] ?? project.scenes[0];
  const columns = project.tracks
    .slice(0, Math.min(ARRANGER_TRACK_COUNT, TRACK_COUNT))
    .map((track) => buildColumn(track, scene));

  return {
    sequence,
    selectedStepIndex: clampedStepIndex,
    scene,
    columns,
  };
}
