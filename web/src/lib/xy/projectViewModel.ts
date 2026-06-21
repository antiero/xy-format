import {
  ImageProject,
  SCENE_COUNT,
  SONG_MAX_CHAIN,
  STEP_TICKS,
  TRACK_COUNT,
  type RawNoteRecord,
} from "./image_writer";
import {
  decodePatternSteps,
  decodeTrackScale,
  noteToDisplayPosition,
  patternTimingMode,
  patternEffectiveLength16ths,
  sceneLength16ths,
  tickToDisplayTick,
  tickToDisplayStep,
  type PatternTimingMode,
  WRITABLE_TRACK_SCALE_BYTES,
} from "./timing";
import { validateProject } from "./validation";

export type XYTrackScale =
  | "1/2"
  | "1"
  | "2"
  | "3"
  | "4"
  | "6"
  | "8"
  | "16"
  | "unknown";

export type ValidationIssue = {
  severity: "info" | "warning" | "error";
  code: string;
  message: string;
  target?: {
    track?: number;
    pattern?: number;
    scene?: number;
    song?: number;
  };
};

export type XYNoteViewModel = {
  id: string;
  noteIndex: number;
  tick: number;
  displayTick: number;
  displayStep: number;
  gateTicks: number;
  note: number;
  noteName: string;
  velocity: number;
  flags0: number;
  flags1: number;
  start16ths: number;
  duration16ths: number;
};

export type XYPatternViewModel = {
  index: number;
  bars: number;
  finalBarSteps: number;
  totalSteps: number;
  rawSteps: number;
  trackScale: XYTrackScale;
  trackScaleRaw: number;
  trackScaleLabel: string;
  trackScaleKnown: boolean;
  trackScaleWriteSupported: boolean;
  timingMode: PatternTimingMode;
  effectiveLength16ths: number;
  notes: XYNoteViewModel[];
  plocks: XYPLockSummary[];
  stepComponents: XYStepComponentSummary[];
};

export type XYTrackViewModel = {
  index: number;
  label: string;
  kind: "instrument" | "aux";
  colorRole: "white" | "red";
  patterns: XYPatternViewModel[];
  midiChannel?: number;
  engineName?: string;
  presetPath?: string;
};

export type XYPLockSummary = {
  step: number;
  count: number;
};

export type XYStepComponentSummary = {
  step: number;
  count: number;
};

export type XYSceneViewModel = {
  index: number;
  present: boolean;
  patternByTrack: number[];
  mutedTracks: boolean[];
  length16ths: number;
};

export type XYSongViewModel = {
  index: number;
  sceneChain: number[];
  loop: boolean;
  supported: boolean;
};

export type XYProjectViewModel = {
  fileName: string;
  modified: boolean;
  tempoBpm: number;
  validation: ValidationIssue[];
  tracks: XYTrackViewModel[];
  scenes: XYSceneViewModel[];
  songs: XYSongViewModel[];
  activeTrackIndex: number;
  activePatternIndex: number;
  activeSceneIndex: number;
  selectedNoteId?: string;
  imageProject: ImageProject;
};

export type XYEdit =
  | { type: "set-active-track"; trackIndex: number }
  | { type: "set-active-pattern"; patternIndex: number }
  | { type: "set-active-scene"; sceneIndex: number }
  | { type: "select-note"; noteId?: string }
  | {
      type: "add-note";
      trackIndex: number;
      patternIndex: number;
      note: Partial<XYNoteViewModel>;
    }
  | {
      type: "add-notes";
      trackIndex: number;
      patternIndex: number;
      notes: Partial<XYNoteViewModel>[];
    }
  | {
      type: "delete-note";
      trackIndex: number;
      patternIndex: number;
      noteId: string;
    }
  | {
      type: "delete-notes";
      trackIndex: number;
      patternIndex: number;
      noteIds: string[];
    }
  | {
      type: "update-note";
      trackIndex: number;
      patternIndex: number;
      noteId: string;
      patch: Partial<XYNoteViewModel>;
    }
  | {
      type: "update-notes";
      trackIndex: number;
      patternIndex: number;
      patches: {
        noteId: string;
        patch: Partial<XYNoteViewModel>;
      }[];
    }
  | {
      type: "set-pattern-steps";
      trackIndex: number;
      patternIndex: number;
      steps: number;
    }
  | {
      type: "set-pattern-bars";
      trackIndex: number;
      patternIndex: number;
      bars: number;
      finalBarSteps: number;
    }
  | {
      type: "set-track-scale";
      trackIndex: number;
      patternIndex: number;
      scale: XYTrackScale;
    }
  | {
      type: "set-scene-pattern";
      sceneIndex: number;
      trackIndex: number;
      patternIndex: number;
    }
  | {
      type: "set-scene-mute";
      sceneIndex: number;
      trackIndex: number;
      muted: boolean;
    }
  | {
      type: "duplicate-scene";
      sourceSceneIndex: number;
      targetSceneIndex: number;
    }
  | { type: "reset-scene"; sceneIndex: number }
  | {
      type: "update-song-chain";
      songIndex: number;
      sceneChain: number[];
      loop?: boolean;
    };

const NOTE_NAMES = [
  "C",
  "C#",
  "D",
  "D#",
  "E",
  "F",
  "F#",
  "G",
  "G#",
  "A",
  "A#",
  "B",
];

export function noteName(note: number): string {
  const name = NOTE_NAMES[((note % 12) + 12) % 12];
  const octave = Math.floor(note / 12) - 1;
  return `${name}${octave}`;
}

function trackLabel(index: number): string {
  return `T${index + 1}`;
}

function trackKind(index: number): "instrument" | "aux" {
  return index < 8 ? "instrument" : "aux";
}

function colorRole(index: number): "white" | "red" {
  return index === 0 || index === 8 || index === 14 || index === 15
    ? "red"
    : "white";
}

function makeNoteView(
  raw: RawNoteRecord,
  pattern: Pick<XYPatternViewModel, "trackScale" | "totalSteps" | "timingMode">,
): XYNoteViewModel {
  const pos = noteToDisplayPosition(
    { tick: raw.tick, gateTicks: raw.gate },
    pattern,
  );
  const displayStep = tickToDisplayStep(raw.tick, pattern.totalSteps);
  const displayTick = tickToDisplayTick(raw.tick, pattern.totalSteps);
  return {
    id: raw.id,
    noteIndex: raw.index,
    tick: raw.tick,
    displayTick,
    displayStep,
    gateTicks: raw.gate,
    note: raw.note,
    noteName: noteName(raw.note),
    velocity: raw.velocity,
    flags0: raw.flags0,
    flags1: raw.flags1,
    start16ths: pos.start16ths,
    duration16ths: pos.duration16ths,
  };
}

export function patternHasStepData(pattern: XYPatternViewModel): boolean {
  return (
    pattern.notes.length > 0 ||
    pattern.plocks.length > 0 ||
    pattern.stepComponents.length > 0
  );
}

export function trackHasStepData(track: XYTrackViewModel): boolean {
  return track.patterns.some(patternHasStepData);
}

export function trackPatternDataCount(track: XYTrackViewModel): number {
  return track.patterns.filter(patternHasStepData).length;
}

export function projectTracksWithStepData(
  project: XYProjectViewModel,
): XYTrackViewModel[] {
  return project.tracks.filter(trackHasStepData);
}

export function projectPatternDataCount(project: XYProjectViewModel): number {
  return projectTracksWithStepData(project).reduce(
    (total, track) => total + trackPatternDataCount(track),
    0,
  );
}

function buildPattern(
  project: ImageProject,
  track: number,
  patternIndex: number,
): XYPatternViewModel {
  const meta = project.getPatternMetadata(track, patternIndex);
  const decodedSteps = decodePatternSteps(meta.steps);
  const decodedScale = decodeTrackScale(meta.scaleRaw);
  const rawNotes = project.getNotes(track, patternIndex);
  const basePattern: XYPatternViewModel = {
    index: patternIndex,
    bars: decodedSteps.bars,
    finalBarSteps: decodedSteps.finalBarSteps,
    totalSteps: decodedSteps.totalSteps,
    rawSteps: decodedSteps.raw,
    trackScale: decodedScale.scale,
    trackScaleRaw: decodedScale.raw,
    trackScaleLabel: decodedScale.label,
    trackScaleKnown: decodedScale.known,
    trackScaleWriteSupported: decodedScale.supportedForWrite,
    timingMode: patternTimingMode(rawNotes),
    effectiveLength16ths: 0,
    notes: [],
    plocks: [],
    stepComponents: [],
  };
  basePattern.effectiveLength16ths = patternEffectiveLength16ths(basePattern);
  basePattern.notes = rawNotes.map((note) => makeNoteView(note, basePattern));
  return basePattern;
}

function buildTracks(project: ImageProject): XYTrackViewModel[] {
  return Array.from({ length: TRACK_COUNT }, (_, index) => {
    const track = index + 1;
    const patternCount = Math.max(1, project.getPatternCount(track));
    const patterns = Array.from({ length: patternCount }, (_, patternIndex) =>
      buildPattern(project, track, patternIndex),
    );
    return {
      index,
      label: trackLabel(index),
      kind: trackKind(index),
      colorRole: colorRole(index),
      patterns,
    };
  });
}

function buildScenes(
  project: ImageProject,
  tracks: XYTrackViewModel[],
): XYSceneViewModel[] {
  const scenes = Array.from({ length: SCENE_COUNT }, (_, sceneIndex) => {
    const row = project.getSceneRow(sceneIndex);
    const scene: XYSceneViewModel = {
      index: sceneIndex,
      present: row.present || sceneIndex === 0,
      patternByTrack: row.patterns,
      mutedTracks: row.mutes,
      length16ths: 0,
    };
    scene.length16ths = sceneLength16ths(scene, tracks);
    return scene;
  });
  return scenes;
}

function clampSelection(project: XYProjectViewModel): void {
  project.activeTrackIndex = Math.max(
    0,
    Math.min(TRACK_COUNT - 1, project.activeTrackIndex),
  );
  const patterns = project.tracks[project.activeTrackIndex]?.patterns ?? [];
  project.activePatternIndex = Math.max(
    0,
    Math.min(Math.max(0, patterns.length - 1), project.activePatternIndex),
  );
  project.activeSceneIndex = Math.max(
    0,
    Math.min(SCENE_COUNT - 1, project.activeSceneIndex),
  );
}

export function buildProjectViewModel(
  imageProject: ImageProject,
  fileName: string,
  previous?: Partial<
    Pick<
      XYProjectViewModel,
      | "activeTrackIndex"
      | "activePatternIndex"
      | "activeSceneIndex"
      | "selectedNoteId"
    >
  >,
  modified = false,
): XYProjectViewModel {
  const tracks = buildTracks(imageProject);
  const project: XYProjectViewModel = {
    fileName,
    modified,
    tempoBpm: imageProject.getTempo(),
    validation: [],
    tracks,
    scenes: [],
    songs: [imageProject.getSongChain(0)],
    activeTrackIndex: previous?.activeTrackIndex ?? 0,
    activePatternIndex: previous?.activePatternIndex ?? 0,
    activeSceneIndex: previous?.activeSceneIndex ?? 0,
    selectedNoteId: previous?.selectedNoteId,
    imageProject,
  };
  project.scenes = buildScenes(imageProject, tracks);
  clampSelection(project);
  project.validation = validateProject(project);
  return project;
}

function findNote(
  project: XYProjectViewModel,
  trackIndex: number,
  patternIndex: number,
  noteId: string,
): XYNoteViewModel {
  const note = project.tracks[trackIndex]?.patterns[patternIndex]?.notes.find(
    (candidate) => candidate.id === noteId,
  );
  if (!note) {
    throw new Error("selected note was not found");
  }
  return note;
}

function findNotes(
  project: XYProjectViewModel,
  trackIndex: number,
  patternIndex: number,
  noteIds: string[],
): XYNoteViewModel[] {
  const wanted = new Set(noteIds);
  return (
    project.tracks[trackIndex]?.patterns[patternIndex]?.notes.filter(
      (candidate) => wanted.has(candidate.id),
    ) ?? []
  );
}

function addNoteToImage(
  project: XYProjectViewModel,
  trackIndex: number,
  patternIndex: number,
  note: Partial<XYNoteViewModel>,
): void {
  const pattern = project.tracks[trackIndex].patterns[patternIndex];
  const factor =
    pattern.trackScale === "unknown"
      ? 1
      : pattern.effectiveLength16ths / pattern.totalSteps;
  const tick =
    note.tick ?? Math.round(((note.start16ths ?? 0) / factor) * STEP_TICKS);
  const gate =
    note.gateTicks ??
    Math.max(1, Math.round(((note.duration16ths ?? 1) / factor) * STEP_TICKS));
  project.imageProject.addNote(trackIndex + 1, {
    tick,
    gate,
    note: note.note ?? 60,
    velocity: note.velocity ?? 100,
    flags0: note.flags0 ?? 0,
    flags1: note.flags1 ?? 0,
    patternIndex,
  });
}

export function applyEdit(
  project: XYProjectViewModel,
  edit: XYEdit,
): XYProjectViewModel {
  const imageProject = project.imageProject;
  let modified = project.modified;
  const selection = {
    activeTrackIndex: project.activeTrackIndex,
    activePatternIndex: project.activePatternIndex,
    activeSceneIndex: project.activeSceneIndex,
    selectedNoteId: project.selectedNoteId,
  };

  switch (edit.type) {
    case "set-active-track":
      selection.activeTrackIndex = edit.trackIndex;
      selection.activePatternIndex = Math.min(
        selection.activePatternIndex,
        Math.max(0, project.tracks[edit.trackIndex]?.patterns.length - 1),
      );
      selection.selectedNoteId = undefined;
      break;
    case "set-active-pattern":
      selection.activePatternIndex = edit.patternIndex;
      selection.selectedNoteId = undefined;
      break;
    case "set-active-scene":
      selection.activeSceneIndex = edit.sceneIndex;
      break;
    case "select-note":
      selection.selectedNoteId = edit.noteId;
      break;
    case "add-note": {
      addNoteToImage(project, edit.trackIndex, edit.patternIndex, edit.note);
      modified = true;
      break;
    }
    case "add-notes": {
      for (const note of edit.notes) {
        addNoteToImage(project, edit.trackIndex, edit.patternIndex, note);
      }
      modified = true;
      break;
    }
    case "delete-note": {
      const note = findNote(
        project,
        edit.trackIndex,
        edit.patternIndex,
        edit.noteId,
      );
      imageProject.deleteNote(
        edit.trackIndex + 1,
        edit.patternIndex,
        note.noteIndex,
      );
      selection.selectedNoteId = undefined;
      modified = true;
      break;
    }
    case "delete-notes": {
      const notes = findNotes(
        project,
        edit.trackIndex,
        edit.patternIndex,
        edit.noteIds,
      ).sort((a, b) => b.noteIndex - a.noteIndex);
      for (const note of notes) {
        imageProject.deleteNote(
          edit.trackIndex + 1,
          edit.patternIndex,
          note.noteIndex,
        );
      }
      selection.selectedNoteId = undefined;
      modified = true;
      break;
    }
    case "update-note": {
      const note = findNote(
        project,
        edit.trackIndex,
        edit.patternIndex,
        edit.noteId,
      );
      imageProject.updateNote(
        edit.trackIndex + 1,
        edit.patternIndex,
        note.noteIndex,
        {
          tick: edit.patch.tick,
          gate: edit.patch.gateTicks,
          note: edit.patch.note,
          velocity: edit.patch.velocity,
        },
      );
      modified = true;
      break;
    }
    case "update-notes": {
      for (const item of edit.patches) {
        const note = findNote(
          project,
          edit.trackIndex,
          edit.patternIndex,
          item.noteId,
        );
        imageProject.updateNote(
          edit.trackIndex + 1,
          edit.patternIndex,
          note.noteIndex,
          {
            tick: item.patch.tick,
            gate: item.patch.gateTicks,
            note: item.patch.note,
            velocity: item.patch.velocity,
          },
        );
      }
      modified = true;
      break;
    }
    case "set-pattern-steps":
      imageProject.setPatternSteps(
        edit.trackIndex + 1,
        edit.steps,
        edit.patternIndex,
      );
      modified = true;
      break;
    case "set-pattern-bars":
      imageProject.setPatternSteps(
        edit.trackIndex + 1,
        (edit.bars - 1) * 16 + edit.finalBarSteps,
        edit.patternIndex,
      );
      modified = true;
      break;
    case "set-track-scale": {
      const raw =
        WRITABLE_TRACK_SCALE_BYTES[
          edit.scale as keyof typeof WRITABLE_TRACK_SCALE_BYTES
        ];
      if (raw === undefined) {
        throw new Error(
          `track scale ${edit.scale} is read-only until its raw byte is decoded`,
        );
      }
      imageProject.setTrackScaleRaw(
        edit.trackIndex + 1,
        raw,
        edit.patternIndex,
      );
      modified = true;
      break;
    }
    case "set-scene-pattern":
      imageProject.setScenePattern(
        edit.sceneIndex,
        edit.trackIndex + 1,
        edit.patternIndex,
      );
      modified = true;
      break;
    case "set-scene-mute":
      imageProject.setSceneMute(
        edit.sceneIndex,
        edit.trackIndex + 1,
        edit.muted,
      );
      modified = true;
      break;
    case "duplicate-scene":
      imageProject.duplicateScene(edit.sourceSceneIndex, edit.targetSceneIndex);
      selection.activeSceneIndex = edit.targetSceneIndex;
      modified = true;
      break;
    case "reset-scene":
      imageProject.resetScene(edit.sceneIndex);
      modified = true;
      break;
    case "update-song-chain":
      imageProject.setSongChain(
        edit.songIndex,
        edit.sceneChain.slice(0, SONG_MAX_CHAIN),
        edit.loop ?? project.songs[edit.songIndex]?.loop ?? true,
      );
      modified = true;
      break;
    default:
      edit satisfies never;
  }

  return buildProjectViewModel(
    imageProject,
    project.fileName,
    selection,
    modified,
  );
}

export function projectSummary(project: XYProjectViewModel): string {
  const activeTracks = projectTracksWithStepData(project);
  const patternCount = projectPatternDataCount(project);
  const presentScenes = project.scenes.filter((scene) => scene.present).length;
  const songCount = project.songs.filter(
    (song) => song.supported && song.sceneChain.length > 0,
  ).length;
  const trackLabel = activeTracks.length === 1 ? "track" : "tracks";
  const patternLabel = patternCount === 1 ? "pattern" : "patterns";
  const sceneLabel = presentScenes === 1 ? "scene" : "scenes";
  const songLabel = songCount === 1 ? "song chain" : "song chains";
  return `${activeTracks.length} ${trackLabel} · ${patternCount} ${patternLabel} · ${presentScenes} ${sceneLabel} · ${songCount} ${songLabel}`;
}
