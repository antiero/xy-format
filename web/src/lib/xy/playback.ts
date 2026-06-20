import { STEP_TICKS } from './image_writer';
import {
  normalizeTickToPattern,
  scaleTo16thsPerStep,
} from './timing';
import type { XYPatternViewModel, XYProjectViewModel } from './projectViewModel';

export type PlaybackScope = 'track' | 'scene';

export type PlaybackEvent = {
  id: string;
  trackIndex: number;
  patternIndex: number;
  noteId: string;
  note: number;
  velocity: number;
  start16ths: number;
  duration16ths: number;
};

export type PlaybackLane = {
  trackIndex: number;
  trackLabel: string;
  colorRole: 'white' | 'red';
  kind: 'instrument' | 'aux';
  patternIndex: number;
  patternLabel: string;
  noteCount: number;
  sceneMuted: boolean;
  scaleLabel: string;
  length16ths: number;
  events: PlaybackEvent[];
};

function noteEvent(trackIndex: number, pattern: XYPatternViewModel): PlaybackEvent[] {
  const factor = scaleTo16thsPerStep(pattern.trackScale) ?? 1;
  return pattern.notes.map((note) => {
    const tick = normalizeTickToPattern(note.tick, pattern.totalSteps);
    return {
      id: `${trackIndex}:${pattern.index}:${note.id}`,
      trackIndex,
      patternIndex: pattern.index,
      noteId: note.id,
      note: note.note,
      velocity: note.velocity,
      start16ths: (tick / STEP_TICKS) * factor,
      duration16ths: Math.max(1 / 16, (note.gateTicks / STEP_TICKS) * factor),
    };
  });
}

export function collectScenePlaybackLanes(
  project: XYProjectViewModel,
  sceneIndex = project.activeSceneIndex,
): PlaybackLane[] {
  const scene = project.scenes[sceneIndex];
  if (!scene) return [];

  return project.tracks
    .map((track) => {
      const patternIndex = scene.patternByTrack[track.index] ?? 0;
      const pattern = track.patterns[patternIndex];
      if (!pattern || pattern.notes.length === 0) return null;
      return {
        trackIndex: track.index,
        trackLabel: track.label,
        colorRole: track.colorRole,
        kind: track.kind,
        patternIndex,
        patternLabel: `P${patternIndex + 1}`,
        noteCount: pattern.notes.length,
        sceneMuted: scene.mutedTracks[track.index] ?? false,
        scaleLabel: pattern.trackScaleLabel,
        length16ths: pattern.effectiveLength16ths,
        events: noteEvent(track.index, pattern),
      } satisfies PlaybackLane;
    })
    .filter((lane): lane is PlaybackLane => lane !== null);
}

export function laneLoopLength16ths(lanes: PlaybackLane[]): number {
  return Math.max(16, ...lanes.map((lane) => lane.length16ths));
}

export function collectLanePlaybackEvents(
  lanes: PlaybackLane[],
  mutedTrackIndexes: ReadonlySet<number> = new Set(),
  soloTrackIndexes: ReadonlySet<number> = new Set(),
): PlaybackEvent[] {
  return lanes
    .filter((lane) => !lane.sceneMuted)
    .filter((lane) => !mutedTrackIndexes.has(lane.trackIndex))
    .filter((lane) => soloTrackIndexes.size === 0 || soloTrackIndexes.has(lane.trackIndex))
    .flatMap((lane) => lane.events)
    .sort((a, b) => a.start16ths - b.start16ths);
}

export function patternLoopLength16ths(pattern: XYPatternViewModel): number {
  return Math.max(1 / 16, pattern.effectiveLength16ths);
}

export function playbackLoopLength16ths(
  project: XYProjectViewModel,
  scope: PlaybackScope,
  trackIndex: number,
  patternIndex: number,
  sceneIndex = project.activeSceneIndex,
): number {
  if (scope === 'track') {
    const pattern = project.tracks[trackIndex]?.patterns[patternIndex];
    return pattern ? patternLoopLength16ths(pattern) : 16;
  }

  return Math.max(16, project.scenes[sceneIndex]?.length16ths ?? 16);
}

export function collectPlaybackEvents(
  project: XYProjectViewModel,
  scope: PlaybackScope,
  trackIndex: number,
  patternIndex: number,
  sceneIndex = project.activeSceneIndex,
): PlaybackEvent[] {
  if (scope === 'track') {
    const pattern = project.tracks[trackIndex]?.patterns[patternIndex];
    return pattern ? noteEvent(trackIndex, pattern).sort((a, b) => a.start16ths - b.start16ths) : [];
  }

  const scene = project.scenes[sceneIndex];
  if (!scene) return [];

  return scene.patternByTrack
    .flatMap((scenePatternIndex, sceneTrackIndex) => {
      if (scene.mutedTracks[sceneTrackIndex]) return [];
      const pattern = project.tracks[sceneTrackIndex]?.patterns[scenePatternIndex];
      return pattern ? noteEvent(sceneTrackIndex, pattern) : [];
    })
    .sort((a, b) => a.start16ths - b.start16ths);
}

export function crossesPlaybackPosition(
  eventStart16ths: number,
  previous16ths: number,
  next16ths: number,
  didWrap: boolean,
): boolean {
  if (didWrap) {
    return eventStart16ths >= previous16ths || eventStart16ths < next16ths;
  }
  return eventStart16ths >= previous16ths && eventStart16ths < next16ths;
}
