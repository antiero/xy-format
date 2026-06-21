import { STEP_TICKS } from "./image_writer";
import { scaleTo16thsPerStep, tickToPlaybackPosition } from "./timing";
import type {
  XYPatternViewModel,
  XYProjectViewModel,
} from "./projectViewModel";

export type PlaybackScope = "track" | "scene";

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
  colorRole: "white" | "red";
  kind: "instrument" | "aux";
  patternIndex: number;
  patternLabel: string;
  noteCount: number;
  sceneMuted: boolean;
  scaleLabel: string;
  length16ths: number;
  events: PlaybackEvent[];
};

function noteEvent(
  trackIndex: number,
  pattern: XYPatternViewModel,
): PlaybackEvent[] {
  const factor = scaleTo16thsPerStep(pattern.trackScale) ?? 1;
  return pattern.notes.map((note) => {
    const tick = tickToPlaybackPosition(
      note.tick,
      pattern.totalSteps,
      pattern.timingMode,
    );
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

export function repeatPlaybackEvents(
  events: PlaybackEvent[],
  patternLength16ths: number,
  loopLength16ths: number,
): PlaybackEvent[] {
  if (events.length === 0 || patternLength16ths <= 0 || loopLength16ths <= 0) {
    return events;
  }

  const repeated: PlaybackEvent[] = [];
  const repeatCount = Math.max(
    1,
    Math.ceil(loopLength16ths / patternLength16ths),
  );
  for (let repeat = 0; repeat < repeatCount; repeat += 1) {
    const offset16ths = repeat * patternLength16ths;
    for (const event of events) {
      const start16ths = event.start16ths + offset16ths;
      if (start16ths >= loopLength16ths) continue;
      repeated.push({
        ...event,
        id: repeat === 0 ? event.id : `${event.id}:r${repeat}`,
        start16ths,
      });
    }
  }
  return repeated.sort((a, b) => a.start16ths - b.start16ths);
}

export function collectScenePlaybackLanes(
  project: XYProjectViewModel,
  sceneIndex = project.activeSceneIndex,
): PlaybackLane[] {
  const scene = project.scenes[sceneIndex];
  if (!scene) return [];
  const loopLength16ths = Math.max(16, scene.length16ths || 16);

  return project.tracks
    .map((track) => {
      const patternIndex = scene.patternByTrack[track.index] ?? 0;
      const pattern = track.patterns[patternIndex];
      if (!pattern || pattern.notes.length === 0) return null;
      const events = noteEvent(track.index, pattern);
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
        events: repeatPlaybackEvents(
          events,
          pattern.effectiveLength16ths,
          loopLength16ths,
        ),
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
    .filter(
      (lane) =>
        soloTrackIndexes.size === 0 || soloTrackIndexes.has(lane.trackIndex),
    )
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
  if (scope === "track") {
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
  if (scope === "track") {
    const pattern = project.tracks[trackIndex]?.patterns[patternIndex];
    return pattern
      ? noteEvent(trackIndex, pattern).sort(
          (a, b) => a.start16ths - b.start16ths,
        )
      : [];
  }

  const scene = project.scenes[sceneIndex];
  if (!scene) return [];

  return scene.patternByTrack
    .flatMap((scenePatternIndex, sceneTrackIndex) => {
      if (scene.mutedTracks[sceneTrackIndex]) return [];
      const pattern =
        project.tracks[sceneTrackIndex]?.patterns[scenePatternIndex];
      return pattern
        ? repeatPlaybackEvents(
            noteEvent(sceneTrackIndex, pattern),
            pattern.effectiveLength16ths,
            Math.max(16, scene.length16ths || 16),
          )
        : [];
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
