import { Midi } from "@tonejs/midi";
import { buildArrangerSequence } from "./arranger";
import { STEP_TICKS } from "./image_writer";
import { outputMidiChannelForTrack, outputMidiNoteForTrack } from "./drumMidi";
import {
  collectSongPlaybackEvents,
  collectSongPlaybackSteps,
  type PlaybackEvent,
} from "./playback";
import type { XYProjectViewModel } from "./projectViewModel";

export type MidiExportOptions = {
  includeDisabledTracks?: boolean;
};

export type MidiFileExport = {
  filename: string;
  bytes: Uint8Array;
  noteCount: number;
  trackIndexes: number[];
};

const MIDI_PPQ = STEP_TICKS * 4;
const INSTRUMENT_TRACK_COUNT = 8;

function clampVelocity(velocity: number): number {
  return Math.max(1 / 127, Math.min(1, velocity / 127));
}

export function midiProjectBaseName(name: string): string {
  const trimmed = name.trim() || "op-xy-project";
  return trimmed.replace(/\.(xy|mid|midi)$/i, "") || "op-xy-project";
}

function collectInstrumentArrangementEvents(
  project: XYProjectViewModel,
  options: MidiExportOptions = {},
): PlaybackEvent[] {
  const sequence = buildArrangerSequence(project);
  const steps = collectSongPlaybackSteps(project, sequence.sceneIndexes);

  return collectSongPlaybackEvents(project, steps, {
    includeMutedTracks: options.includeDisabledTracks,
    instrumentTrackCount: INSTRUMENT_TRACK_COUNT,
  }).map((event) => ({
    ...event,
    id: event.id.replace(/^song:/, "arr:"),
  }));
}

function patternEvents(
  project: XYProjectViewModel,
  trackIndex: number,
  patternIndex: number,
): PlaybackEvent[] {
  const pattern = project.tracks[trackIndex]?.patterns[patternIndex];
  if (!pattern || pattern.notes.length === 0) return [];

  return pattern.notes
    .map((note) => ({
      id: `pattern:${trackIndex}:${patternIndex}:${note.id}`,
      trackIndex,
      patternIndex,
      noteId: note.id,
      note: note.note,
      velocity: note.velocity,
      start16ths: note.start16ths,
      duration16ths: note.duration16ths,
    }))
    .sort((a, b) => a.start16ths - b.start16ths);
}

function eventsByTrack(events: PlaybackEvent[]): Map<number, PlaybackEvent[]> {
  const grouped = new Map<number, PlaybackEvent[]>();
  for (const event of events) {
    const existing = grouped.get(event.trackIndex) ?? [];
    existing.push(event);
    grouped.set(event.trackIndex, existing);
  }
  return grouped;
}

function setupMidi(name: string, tempoBpm: number): Midi {
  const midi = new Midi();
  midi.header.fromJSON({
    name,
    ppq: MIDI_PPQ,
    meta: [],
    tempos: [{ bpm: Math.max(10, tempoBpm || 120), ticks: 0 }],
    timeSignatures: [{ ticks: 0, timeSignature: [4, 4] }],
    keySignatures: [],
  });
  return midi;
}

function addEventsToTrack(
  midi: Midi,
  trackIndex: number,
  events: PlaybackEvent[],
): void {
  const track = midi.addTrack();
  track.name = `Track ${trackIndex + 1}`;
  track.channel = outputMidiChannelForTrack(trackIndex);

  for (const event of events) {
    track.addNote({
      midi: outputMidiNoteForTrack(trackIndex, event.note),
      ticks: Math.max(0, Math.round(event.start16ths * STEP_TICKS)),
      durationTicks: Math.max(1, Math.round(event.duration16ths * STEP_TICKS)),
      velocity: clampVelocity(event.velocity),
    });
  }
}

function createMidiFile(
  name: string,
  project: XYProjectViewModel,
  grouped: Map<number, PlaybackEvent[]>,
  filename: string,
): MidiFileExport {
  const midi = setupMidi(name, project.tempoBpm);
  const trackIndexes = [...grouped.keys()].sort((a, b) => a - b);
  let noteCount = 0;

  for (const trackIndex of trackIndexes) {
    const events = grouped.get(trackIndex) ?? [];
    if (events.length === 0) continue;
    addEventsToTrack(midi, trackIndex, events);
    noteCount += events.length;
  }

  return {
    filename,
    bytes: midi.toArray(),
    noteCount,
    trackIndexes,
  };
}

export function exportableMidiNoteCount(
  project: XYProjectViewModel,
  options: MidiExportOptions = {},
): number {
  return collectInstrumentArrangementEvents(project, options).length;
}

export function exportSongMidi(
  project: XYProjectViewModel,
  projectName = project.fileName,
  options: MidiExportOptions = {},
): MidiFileExport {
  const name = midiProjectBaseName(projectName);
  return createMidiFile(
    name,
    project,
    eventsByTrack(collectInstrumentArrangementEvents(project, options)),
    `${name}.mid`,
  );
}

export function exportTrackMidis(
  project: XYProjectViewModel,
  options: MidiExportOptions = {},
): MidiFileExport[] {
  const grouped = eventsByTrack(
    collectInstrumentArrangementEvents(project, options),
  );

  return [...grouped.entries()]
    .filter(([, events]) => events.length > 0)
    .sort(([a], [b]) => a - b)
    .map(([trackIndex, events]) =>
      createMidiFile(
        `Track ${trackIndex + 1}`,
        project,
        new Map([[trackIndex, events]]),
        `track${trackIndex + 1}.mid`,
      ),
    );
}

export function exportPatternMidis(
  project: XYProjectViewModel,
  projectName = project.fileName,
  options: MidiExportOptions = {},
): MidiFileExport[] {
  const name = midiProjectBaseName(projectName);
  const includedTrackIndexes = new Set(
    collectInstrumentArrangementEvents(project, options).map(
      (event) => event.trackIndex,
    ),
  );
  const files: MidiFileExport[] = [];

  for (const track of project.tracks.slice(0, INSTRUMENT_TRACK_COUNT)) {
    if (!includedTrackIndexes.has(track.index)) continue;

    for (const pattern of track.patterns) {
      const events = patternEvents(project, track.index, pattern.index);
      if (events.length === 0) continue;
      files.push(
        createMidiFile(
          `Track ${track.index + 1} Pattern ${pattern.index + 1}`,
          project,
          new Map([[track.index, events]]),
          `${name}-trk${track.index + 1}-pt-${pattern.index + 1}.mid`,
        ),
      );
    }
  }

  return files;
}
