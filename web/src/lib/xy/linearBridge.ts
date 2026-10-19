import {
  buildArrangementFromBytes,
  ImageProject,
  STEP_TICKS,
  TRACK_COUNT,
  type PatternNoteInput,
  type TrackPatternMap,
} from "./image_writer";
import {
  applyEdit,
  buildProjectViewModel,
  type XYProjectViewModel,
} from "./projectViewModel";
import {
  loadPresetStruct,
  OP_XY_FACTORY_PRESET_CATALOG,
  opXyPresetById,
} from "./opXyPresets";

export type LinearNotePayload = {
  scene: number;
  track: number;
  step: number; // 1..64
  tick: number; // microTick 0..119
  note: number; // MIDI note 0..127
  velocity: number; // 1..127
  length: number; // duration in 16th steps
};

export type LinearSequencePayload = {
  filename?: string;
  tempoBPM?: number;
  bars?: number;
  sceneCount?: number;
  notes: LinearNotePayload[];
  /** OP-XY preset per track, keyed by 0-based track index (native Edit tab). */
  presetIdsByTrack?: Record<string, string>;
};

export function exportActiveSongData(
  project: XYProjectViewModel | null,
): string {
  if (!project) {
    return JSON.stringify({ error: "No project loaded" });
  }

  const sceneChain =
    project.songs[0]?.sceneChain && project.songs[0].sceneChain.length > 0
      ? project.songs[0].sceneChain
      : [0];

  const payload = {
    fileName: project.fileName,
    tempoBpm: project.tempoBpm,
    sceneChain,
    scenes: project.scenes.map((s) => ({
      index: s.index,
      present: s.present,
      patternByTrack: s.patternByTrack,
      mutedTracks: s.mutedTracks,
      length16ths: s.length16ths,
    })),
    tracks: project.tracks.map((t) => ({
      index: t.index,
      label: t.label,
      patterns: t.patterns.map((p) => ({
        index: p.index,
        bars: p.bars,
        totalSteps: p.totalSteps,
        // So the native Edit tab can name tracks and pick matching voices.
        presetId: p.presetId,
        presetLabel: p.presetLabel,
        presetCategory: opXyPresetById(p.presetId)?.category ?? null,
        notes: p.notes.map((n) => ({
          note: n.note,
          velocity: n.velocity,
          start16ths: n.start16ths,
          duration16ths: n.duration16ths,
          displayStep: n.displayStep,
          displayTick: n.displayTick,
        })),
      })),
    })),
  };

  return JSON.stringify(payload);
}

/** The factory preset browser, for the native Edit tab's picker. */
export function presetCatalogJSON(): string {
  return JSON.stringify(OP_XY_FACTORY_PRESET_CATALOG);
}

/**
 * Applies the presets the native Edit tab chose to every pattern of their
 * tracks. Presets that can't be applied (unknown, or needing a newer OP-XY OS
 * than the project) are skipped and reported, leaving that track as it was.
 */
export async function applyLinearSequencePresets(
  project: XYProjectViewModel,
  presetIdsByTrack: Record<string, string> | undefined,
  loadStruct: (
    presetId: string,
    targetHeader?: Uint8Array,
  ) => Promise<Uint8Array> = loadPresetStruct,
): Promise<{ project: XYProjectViewModel; skipped: string[] }> {
  const skipped: string[] = [];
  let next = project;
  for (const [key, presetId] of Object.entries(presetIdsByTrack ?? {})) {
    const trackIndex = Number(key);
    if (!Number.isInteger(trackIndex) || trackIndex < 0 || trackIndex >= 8) {
      continue;
    }
    try {
      const donorStruct = await loadStruct(
        presetId,
        next.imageProject.header,
      );
      next = applyEdit(next, {
        type: "set-track-preset",
        trackIndex,
        presetId,
        donorStruct,
      });
    } catch (error) {
      console.warn(`Skipped preset ${presetId} on track ${trackIndex + 1}`, error);
      skipped.push(presetId);
    }
  }
  return { project: next, skipped };
}

export function buildLinearSequenceProject(
  baselineBytes: Uint8Array,
  payload: LinearSequencePayload,
  fileName: string = "PianoRoll.xy",
): XYProjectViewModel {
  const sceneCount = Math.max(1, Math.min(16, payload.sceneCount ?? 1));
  const trackPatterns: TrackPatternMap = {};

  // For instrument tracks (1..8)
  for (let track = 1; track <= 8; track++) {
    const patterns: Array<{
      steps: number;
      bars: number;
      notes: PatternNoteInput[];
    }> = [];
    for (let s = 0; s < sceneCount; s++) {
      patterns.push({
        steps: 64,
        bars: 4,
        notes: [],
      });
    }
    trackPatterns[track] = patterns;
  }

  // Populate notes
  for (const n of payload.notes ?? []) {
    if (n.track < 0 || n.track >= 8) continue;
    const track = n.track + 1; // 1-based
    if (n.scene < 0 || n.scene >= sceneCount) continue;
    const pattern = trackPatterns[track]?.[n.scene];
    if (!pattern || !("notes" in pattern) || !pattern.notes) continue;

    const gateTicks = Math.max(1, Math.round(n.length * STEP_TICKS));
    pattern.notes.push({
      step: n.step,
      note: n.note,
      velocity: n.velocity,
      tickOffset: n.tick || 0,
      gateTicks,
    });
  }

  // Aux tracks (9..16)
  for (let track = 9; track <= TRACK_COUNT; track++) {
    trackPatterns[track] = [{ steps: 64, bars: 4, notes: [] }];
  }

  const arrangementBytes = buildArrangementFromBytes(
    baselineBytes,
    trackPatterns,
  );
  const imageProject = ImageProject.fromBytes(arrangementBytes);

  if (payload.tempoBPM && payload.tempoBPM > 0) {
    imageProject.setTempo(payload.tempoBPM);
  }

  // Set scenes
  for (let s = 0; s < sceneCount; s++) {
    for (let t = 1; t <= 8; t++) {
      imageProject.setScenePattern(s + 1, t, s);
    }
  }

  // Set song chain (songIndex is 0-based)
  const chain = Array.from({ length: sceneCount }, (_, i) => i);
  imageProject.setSongChain(0, chain);

  return buildProjectViewModel(imageProject, fileName);
}
