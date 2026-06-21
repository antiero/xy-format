import {
  parseMidi,
  type MidiData,
  type MidiEvent,
  type MidiNoteOffEvent,
  type MidiNoteOnEvent,
  type MidiSetTempoEvent,
} from 'midi-file';
import {
  buildArrangementFromBytes,
  ImageProject,
  STEP_TICKS,
  TRACK_COUNT,
  type PatternNoteInput,
  type TrackPatternMap,
} from './image_writer';
import { buildProjectViewModel, type XYProjectViewModel } from './projectViewModel';

type Role = 'drum' | 'bass' | 'lead' | 'chord';
type LaneKey = `${number}:${number}`;

type MidiNote = {
  absTick: number;
  note: number;
  velocity: number;
  gateTicks: number;
  channel: number;
};

type PartCandidate = {
  key: [number, number];
  notesAll: MidiNote[];
  notesWindow: MidiNote[];
  noteCount: number;
  uniquePitches: number;
  pitchMin: number;
  pitchMax: number;
  meanPitch: number;
  activeBars: number;
  polyphonyRatio: number;
  avgNotesPerOnset: number;
  isDrumChannel: boolean;
  drumNoteRatio: number;
  utilityScore: number;
  roleScores: Record<Role, number>;
  fingerprint: Set<string>;
};

type SelectionResult = {
  assignments: Map<number, PartCandidate>;
  rankedParts: PartCandidate[];
  droppedDuplicates: Array<[PartCandidate, PartCandidate, number]>;
};

export type MidiImportSummary = {
  bpm: number;
  ticksPerBeat: number;
  patterns: number;
  totalBars: number;
  importedNotes: number;
  activeTracks: number[];
  notesPerPatternByTrack: Record<number, number[]>;
};

export type MidiImportResult = {
  project: XYProjectViewModel;
  summary: MidiImportSummary;
};

export type MidiImportOptions = {
  bpmOverride?: number;
};

const ROLE_SLOTS: Record<number, Role> = {
  1: 'drum',
  2: 'drum',
  3: 'bass',
  4: 'lead',
  5: 'lead',
  6: 'lead',
  7: 'chord',
  8: 'chord',
};

const SINGLE_ROLE_SLOT: Record<Role, number> = {
  drum: 1,
  bass: 3,
  lead: 4,
  chord: 7,
};

const ROLE_MIN_SCORE: Record<Role, number> = {
  drum: 40,
  bass: 18,
  lead: 12,
  chord: 16,
};

const ROLE_MIN_NOTES: Record<Role, number> = {
  drum: 12,
  bass: 12,
  lead: 10,
  chord: 18,
};

const ROLE_MIN_ACTIVE_BARS: Record<Role, number> = {
  drum: 3,
  bass: 3,
  lead: 2,
  chord: 3,
};

const MAX_NOTES_PER_PATTERN = 120;

const GM_TO_OPXY_DRUM: Record<number, number> = {
  35: 48,
  36: 48,
  37: 52,
  38: 50,
  39: 53,
  40: 51,
  41: 60,
  42: 56,
  43: 61,
  44: 57,
  45: 62,
  46: 58,
  47: 63,
  48: 64,
  49: 54,
  50: 65,
  51: 55,
  52: 66,
  53: 67,
  54: 57,
  55: 68,
  56: 69,
  57: 54,
};

let baselineBytesPromise: Promise<Uint8Array> | null = null;

function remapDrumNote(gmNote: number): number {
  return GM_TO_OPXY_DRUM[gmNote] ?? Math.max(48, Math.min(71, gmNote));
}

function isNoteOn(event: MidiEvent): event is MidiNoteOnEvent {
  return event.type === 'noteOn';
}

function isNoteOff(event: MidiEvent): event is MidiNoteOffEvent {
  return event.type === 'noteOff';
}

function isSetTempo(event: MidiEvent): event is MidiSetTempoEvent {
  return event.type === 'setTempo';
}

function laneKey(trackIndex: number, channel: number): LaneKey {
  return `${trackIndex}:${channel}`;
}

function splitLaneKey(key: LaneKey): [number, number] {
  const [track, channel] = key.split(':').map((part) => Number(part));
  return [track, channel];
}

function jaccardSimilarity(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 && b.size === 0) return 1;
  if (a.size === 0 || b.size === 0) return 0;
  let intersection = 0;
  for (const item of a) {
    if (b.has(item)) intersection++;
  }
  const union = a.size + b.size - intersection;
  return union === 0 ? 0 : intersection / union;
}

function extractMidiParts(midi: MidiData): Map<LaneKey, MidiNote[]> {
  const laneNotes = new Map<LaneKey, MidiNote[]>();
  const pending = new Map<string, Array<[number, number]>>();

  midi.tracks.forEach((track, trackIndex) => {
    let absTick = 0;
    for (const event of track) {
      absTick += event.deltaTime;
      if (isNoteOn(event) && event.velocity > 0) {
        const key = `${trackIndex}:${event.channel}:${event.noteNumber}`;
        const starts = pending.get(key) ?? [];
        starts.push([absTick, event.velocity]);
        pending.set(key, starts);
        continue;
      }

      if (isNoteOff(event) || (isNoteOn(event) && event.velocity === 0)) {
        const key = `${trackIndex}:${event.channel}:${event.noteNumber}`;
        const starts = pending.get(key);
        if (!starts || starts.length === 0) continue;
        const [onset, velocity] = starts.pop() as [number, number];
        if (starts.length === 0) {
          pending.delete(key);
        }
        const lane = laneKey(trackIndex, event.channel);
        const notes = laneNotes.get(lane) ?? [];
        notes.push({
          absTick: onset,
          note: event.noteNumber,
          velocity,
          gateTicks: Math.max(absTick - onset, 1),
          channel: event.channel,
        });
        laneNotes.set(lane, notes);
      }
    }
  });

  for (const notes of laneNotes.values()) {
    notes.sort((a, b) => a.absTick - b.absTick || a.note - b.note);
  }

  return laneNotes;
}

function selectBarWindow(notes: MidiNote[], midiTpb: number, startBar: number, numBars: number): MidiNote[] {
  const ticksPerBar = midiTpb * 4;
  const lo = startBar * ticksPerBar;
  const hi = (startBar + numBars) * ticksPerBar;
  return notes.filter((note) => lo <= note.absTick && note.absTick < hi);
}

function partFingerprint(notesWindow: MidiNote[], midiTpb: number, startBar: number, isDrumChannel: boolean): Set<string> {
  const sig = new Set<string>();
  if (notesWindow.length === 0) return sig;

  const ticksPerBar = midiTpb * 4;
  const lo = startBar * ticksPerBar;
  const scale = 1920 / midiTpb;
  for (const note of notesWindow) {
    const relTick = note.absTick - lo;
    const xyTick = Math.round(relTick * scale);
    const qTick = Math.round(xyTick / 120) * 120;
    const pitch = isDrumChannel ? remapDrumNote(note.note) : note.note;
    sig.add(`${qTick}:${pitch}`);
  }
  return sig;
}

function computeRoleScores(args: {
  isDrumChannel: boolean;
  drumNoteRatio: number;
  noteCount: number;
  activeBars: number;
  meanPitch: number;
  uniquePitches: number;
  polyphonyRatio: number;
  avgNotesPerOnset: number;
  pitchSpan: number;
}): Record<Role, number> {
  const {
    isDrumChannel,
    drumNoteRatio,
    noteCount,
    activeBars,
    meanPitch,
    uniquePitches,
    polyphonyRatio,
    avgNotesPerOnset,
    pitchSpan,
  } = args;

  let drum = isDrumChannel ? 120 : -75;
  drum += drumNoteRatio * 35;
  drum += Math.min(noteCount / 12, 25);
  drum += activeBars * 1.2;
  if (uniquePitches <= 2) drum -= 8;

  if (isDrumChannel) {
    return { drum, bass: -1000, lead: -1000, chord: -1000 };
  }

  const lowPitchPref = Math.max(0, 72 - meanPitch);
  let bass = lowPitchPref * 1.7;
  bass += activeBars * 1.4;
  bass += Math.min(noteCount / 18, 20);
  bass += polyphonyRatio < 0.2 ? 10 : -20 * polyphonyRatio;
  bass -= Math.max(0, meanPitch - 76) * 2.2;

  let chord = polyphonyRatio * 120;
  chord += Math.max(0, avgNotesPerOnset - 1) * 32;
  chord += Math.min(uniquePitches, 24) * 0.8;
  chord += activeBars * 1.2;
  if (meanPitch < 45) chord -= 22;
  if (noteCount < 24) chord -= (24 - noteCount) * 2.4;
  if (activeBars < 3) chord -= (3 - activeBars) * 20;

  let lead = Math.min(noteCount / 16, 25);
  lead += activeBars * 1.1;
  lead += Math.min(pitchSpan, 36) * 0.7;
  lead += 52 <= meanPitch && meanPitch <= 90 ? 10 : -Math.abs(meanPitch - 71) * 0.55;
  lead += polyphonyRatio < 0.35 ? 8 : -(polyphonyRatio - 0.35) * 30;

  return { drum, bass, lead, chord };
}

function candidateUtility(args: {
  noteCount: number;
  activeBars: number;
  uniquePitches: number;
  isDrumChannel: boolean;
  pitchSpan: number;
}): number {
  let score = 0;
  score += args.activeBars * 3.2;
  score += Math.min(args.noteCount / 10, 35);
  score += Math.min(args.uniquePitches, 32) * 0.9;
  score += Math.min(args.pitchSpan, 48) * 0.3;
  if (args.isDrumChannel) score += 4;
  return score;
}

function buildPartCandidates(
  laneNotes: Map<LaneKey, MidiNote[]>,
  midiTpb: number,
  startBar: number,
  totalBars: number,
): PartCandidate[] {
  const ticksPerBar = midiTpb * 4;
  const lo = startBar * ticksPerBar;
  const candidates: PartCandidate[] = [];

  for (const [key, notesAll] of laneNotes) {
    const notesWindow = selectBarWindow(notesAll, midiTpb, startBar, totalBars);
    if (notesWindow.length < 3) continue;

    const pitches = notesWindow.map((note) => note.note);
    const noteCount = notesWindow.length;
    const uniquePitches = new Set(pitches).size;
    const pitchMin = Math.min(...pitches);
    const pitchMax = Math.max(...pitches);
    const meanPitch = pitches.reduce((sum, pitch) => sum + pitch, 0) / noteCount;
    const pitchSpan = pitchMax - pitchMin;
    const bars = new Set<number>();
    for (const note of notesWindow) {
      const bar = Math.max(0, Math.min(totalBars - 1, Math.floor((note.absTick - lo) / ticksPerBar)));
      bars.add(bar);
    }

    const onsetCounts = new Map<number, number>();
    for (const note of notesWindow) {
      onsetCounts.set(note.absTick, (onsetCounts.get(note.absTick) ?? 0) + 1);
    }
    const chordOnsets = Array.from(onsetCounts.values()).filter((count) => count > 1).length;
    const polyphonyRatio = chordOnsets / Math.max(1, onsetCounts.size);
    const avgNotesPerOnset = noteCount / Math.max(1, onsetCounts.size);

    const [, channel] = splitLaneKey(key);
    const isDrumChannel = channel === 9;
    const drumNoteHits = pitches.filter((pitch) => 27 <= pitch && pitch <= 87).length;
    const drumNoteRatio = drumNoteHits / noteCount;
    const roleScores = computeRoleScores({
      isDrumChannel,
      drumNoteRatio,
      noteCount,
      activeBars: bars.size,
      meanPitch,
      uniquePitches,
      polyphonyRatio,
      avgNotesPerOnset,
      pitchSpan,
    });
    const utilityScore = candidateUtility({
      noteCount,
      activeBars: bars.size,
      uniquePitches,
      isDrumChannel,
      pitchSpan,
    });

    candidates.push({
      key: splitLaneKey(key),
      notesAll,
      notesWindow,
      noteCount,
      uniquePitches,
      pitchMin,
      pitchMax,
      meanPitch,
      activeBars: bars.size,
      polyphonyRatio,
      avgNotesPerOnset,
      isDrumChannel,
      drumNoteRatio,
      utilityScore,
      roleScores,
      fingerprint: partFingerprint(notesWindow, midiTpb, startBar, isDrumChannel),
    });
  }

  candidates.sort((a, b) => (
    b.utilityScore - a.utilityScore ||
    b.noteCount - a.noteCount ||
    b.activeBars - a.activeBars
  ));
  return candidates;
}

function dedupeCandidates(candidates: PartCandidate[]): [PartCandidate[], Array<[PartCandidate, PartCandidate, number]>] {
  const kept: PartCandidate[] = [];
  const dropped: Array<[PartCandidate, PartCandidate, number]> = [];

  for (const candidate of candidates) {
    let duplicateOf: PartCandidate | undefined;
    let duplicateSimilarity = 0;
    for (const ref of kept) {
      if (candidate.isDrumChannel !== ref.isDrumChannel) continue;
      const similarity = jaccardSimilarity(candidate.fingerprint, ref.fingerprint);
      if (similarity >= 0.92 && candidate.noteCount <= ref.noteCount * 1.25) {
        duplicateOf = ref;
        duplicateSimilarity = similarity;
        break;
      }
    }
    if (duplicateOf) {
      dropped.push([candidate, duplicateOf, duplicateSimilarity]);
    } else {
      kept.push(candidate);
    }
  }

  return [kept, dropped];
}

function roleCandidateOk(candidate: PartCandidate, role: Role, totalBars: number, relaxed = false): boolean {
  let minNotes = ROLE_MIN_NOTES[role];
  let minBars = ROLE_MIN_ACTIVE_BARS[role];
  if (relaxed) {
    minNotes = Math.max(6, Math.floor(minNotes / 2));
    minBars = Math.max(1, minBars - 1);
  }
  if (candidate.noteCount < minNotes || candidate.activeBars < minBars) return false;

  if (role === 'drum') {
    if (candidate.isDrumChannel) return true;
    if (!relaxed) return false;
    return (
      candidate.roleScores.drum >= ROLE_MIN_SCORE.drum * 0.7 &&
      candidate.polyphonyRatio <= 0.08 &&
      candidate.meanPitch <= 58 &&
      candidate.pitchMax - candidate.pitchMin <= 20
    );
  }
  if (role === 'bass') {
    if (candidate.isDrumChannel) return false;
    return candidate.meanPitch <= 62 && candidate.polyphonyRatio <= (relaxed ? 0.3 : 0.2);
  }
  if (role === 'lead') {
    if (candidate.isDrumChannel) return false;
    return candidate.meanPitch >= (relaxed ? 45 : 50) && candidate.pitchMax >= 55;
  }
  if (candidate.isDrumChannel) return false;
  const minPoly = relaxed ? 0.12 : 0.2;
  const minOnsetStack = relaxed ? 1.25 : 1.35;
  const minCoverage = Math.max(2, Math.round(totalBars * (relaxed ? 0.12 : 0.18)));
  return (
    (candidate.polyphonyRatio >= minPoly || candidate.avgNotesPerOnset >= minOnsetStack) &&
    candidate.activeBars >= minCoverage
  );
}

function assignPartsToSlots(candidates: PartCandidate[], totalBars: number): Map<number, PartCandidate> {
  const remaining = [...candidates];
  const assignments = new Map<number, PartCandidate>();

  if (remaining.length === 1) {
    const candidate = remaining[0];
    if (candidate.isDrumChannel) {
      assignments.set(1, candidate);
      return assignments;
    }
    const roles: Role[] = ['bass', 'lead', 'chord'];
    const eligible = roles.filter((role) => roleCandidateOk(candidate, role, totalBars, true));
    const role = (eligible.length ? eligible : roles).reduce((best, roleName) => (
      candidate.roleScores[roleName] > candidate.roleScores[best] ? roleName : best
    ));
    assignments.set(SINGLE_ROLE_SLOT[role], candidate);
    return assignments;
  }

  function pickForRole(role: Role, relaxed = false): PartCandidate | undefined {
    const pool = remaining.filter((candidate) => roleCandidateOk(candidate, role, totalBars, relaxed));
    if (pool.length === 0) return undefined;
    pool.sort((a, b) => (
      b.roleScores[role] - a.roleScores[role] ||
      b.utilityScore - a.utilityScore ||
      b.noteCount - a.noteCount ||
      a.key[0] - b.key[0] ||
      a.key[1] - b.key[1]
    ));
    const best = pool[0];
    if (best.roleScores[role] < ROLE_MIN_SCORE[role] * (relaxed ? 0.75 : 1)) return undefined;
    remaining.splice(remaining.indexOf(best), 1);
    return best;
  }

  for (const slot of [1, 2, 3, 4, 5, 6, 7, 8]) {
    const picked = pickForRole(ROLE_SLOTS[slot]);
    if (picked) assignments.set(slot, picked);
  }

  for (const slot of [1, 2, 3, 4, 5, 6, 7, 8]) {
    if (assignments.has(slot)) continue;
    const picked = pickForRole(ROLE_SLOTS[slot], true);
    if (picked) assignments.set(slot, picked);
  }

  for (const slot of [4, 5, 6]) {
    if (assignments.has(slot) || remaining.length === 0) continue;
    remaining.sort((a, b) => (
      b.roleScores.lead - a.roleScores.lead ||
      b.utilityScore - a.utilityScore ||
      b.noteCount - a.noteCount ||
      b.activeBars - a.activeBars
    ));
    const best = remaining[0];
    if (best.utilityScore < 8) continue;
    remaining.shift();
    assignments.set(slot, best);
  }

  return assignments;
}

function selectBestParts(laneNotes: Map<LaneKey, MidiNote[]>, midiTpb: number, startBar: number, totalBars: number): SelectionResult {
  const candidates = buildPartCandidates(laneNotes, midiTpb, startBar, totalBars);
  const [rankedParts, droppedDuplicates] = dedupeCandidates(candidates);
  return {
    assignments: assignPartsToSlots(rankedParts, totalBars),
    rankedParts,
    droppedDuplicates,
  };
}

function midiToXyNotes(midiNotes: MidiNote[], midiTpb: number, startBar: number, isDrum: boolean): PatternNoteInput[] {
  const ticksPerBarMidi = midiTpb * 4;
  const barOffset = startBar * ticksPerBarMidi;
  const scale = 1920 / midiTpb;
  const xyNotes: PatternNoteInput[] = [];

  for (const note of midiNotes) {
    const midiTickInPattern = note.absTick - barOffset;
    let xyTick = Math.round(midiTickInPattern * scale);
    xyTick = Math.round(xyTick / STEP_TICKS) * STEP_TICKS;
    const step0 = Math.floor(xyTick / STEP_TICKS);
    const step = step0 + 1;
    const tickOffset = xyTick % STEP_TICKS;
    if (step < 1 || step > 64) continue;

    let gateTicks = Math.round(note.gateTicks * scale);
    gateTicks = Math.max(STEP_TICKS, Math.round(gateTicks / STEP_TICKS) * STEP_TICKS);
    xyNotes.push({
      step,
      note: isDrum ? remapDrumNote(note.note) : note.note,
      velocity: Math.max(1, Math.min(127, note.velocity)),
      tickOffset,
      gateTicks,
    });
  }

  xyNotes.sort((a, b) => (
    (a.step - 1) * STEP_TICKS + (a.tickOffset ?? 0) -
    ((b.step - 1) * STEP_TICKS + (b.tickOffset ?? 0))
  ));
  return xyNotes;
}

function deriveSecondaryDrumWindow(notesWindow: MidiNote[]): MidiNote[] {
  const highPerc: MidiNote[] = [];
  const baseHits: MidiNote[] = [];
  for (const note of notesWindow) {
    const mapped = remapDrumNote(note.note);
    if (mapped >= 56 || [54, 55, 67, 68, 69, 70, 71].includes(mapped)) {
      highPerc.push(note);
    } else {
      baseHits.push(note);
    }
  }
  if (highPerc.length > 0) return highPerc;
  if (baseHits.length <= 1) return baseHits;
  return baseHits.filter((_, index) => index % 2 === 1) || baseHits.slice(0, 1);
}

function deriveSecondaryChordWindow(notesWindow: MidiNote[]): MidiNote[] {
  const byOnset = new Map<number, MidiNote[]>();
  for (const note of notesWindow) {
    const group = byOnset.get(note.absTick) ?? [];
    group.push(note);
    byOnset.set(note.absTick, group);
  }

  const upperVoices: MidiNote[] = [];
  for (const onset of Array.from(byOnset.keys()).sort((a, b) => a - b)) {
    const group = [...(byOnset.get(onset) ?? [])].sort((a, b) => a.note - b.note);
    if (group.length >= 2) {
      upperVoices.push(...group.slice(-Math.max(1, Math.floor(group.length / 2))));
    }
  }
  if (upperVoices.length > 0) return upperVoices;

  const pitches = notesWindow.map((note) => note.note).sort((a, b) => a - b);
  const median = pitches[Math.floor(pitches.length / 2)];
  const highNotes = notesWindow.filter((note) => note.note >= median);
  if (highNotes.length > 0) return highNotes;
  return notesWindow.filter((_, index) => index % 2 === 1) || notesWindow.slice(0, 1);
}

function buildTrackPatterns(selection: SelectionResult, midiTpb: number, startBar: number, numPatterns: number): Map<number, Array<PatternNoteInput[] | null>> {
  const trackPatterns = new Map<number, Array<PatternNoteInput[] | null>>();
  const drumPrimary = selection.assignments.get(1) ?? selection.assignments.get(2);
  const chordPrimary = selection.assignments.get(7) ?? selection.assignments.get(8);
  const deriveMissingRoles = new Set(
    Array.from(selection.assignments.values()).map((candidate) => candidate.key.join(':')),
  ).size > 1;

  for (let slot = 1; slot <= 8; slot++) {
    const role = ROLE_SLOTS[slot];
    const candidate = selection.assignments.get(slot);
    const patterns: Array<PatternNoteInput[] | null> = [];

    for (let patternIndex = 0; patternIndex < numPatterns; patternIndex++) {
      const patternStart = startBar + patternIndex * 4;
      let sourceNotes: MidiNote[] = [];
      if (candidate) {
        sourceNotes = selectBarWindow(candidate.notesAll, midiTpb, patternStart, 4);
      } else if (role === 'drum' && drumPrimary && deriveMissingRoles) {
        const base = selectBarWindow(drumPrimary.notesAll, midiTpb, patternStart, 4);
        sourceNotes = deriveSecondaryDrumWindow(base);
      } else if (role === 'chord' && chordPrimary && deriveMissingRoles) {
        const base = selectBarWindow(chordPrimary.notesAll, midiTpb, patternStart, 4);
        sourceNotes = deriveSecondaryChordWindow(base);
      }

      const xyNotes = sourceNotes.length > 0
        ? midiToXyNotes(sourceNotes, midiTpb, patternStart, role === 'drum')
        : [];
      patterns.push(xyNotes.length > 0 ? xyNotes.slice(0, MAX_NOTES_PER_PATTERN) : null);
    }
    trackPatterns.set(slot, patterns);
  }

  return trackPatterns;
}

function autoDetectPatterns(laneNotes: Map<LaneKey, MidiNote[]>, midiTpb: number, startBar: number): number {
  const ticksPerBar = midiTpb * 4;
  let maxTick = 0;
  for (const notes of laneNotes.values()) {
    for (const note of notes) {
      maxTick = Math.max(maxTick, note.absTick + note.gateTicks);
    }
  }
  const totalBars = Math.max(1, Math.ceil(maxTick / ticksPerBar));
  const remainingBars = Math.max(1, totalBars - startBar);
  return Math.max(1, Math.min(9, Math.ceil(remainingBars / 4)));
}

function firstTempoBpm(midi: MidiData): number {
  for (const track of midi.tracks) {
    let absTick = 0;
    for (const event of track) {
      absTick += event.deltaTime;
      if (absTick === 0 && isSetTempo(event)) {
        return 60_000_000 / event.microsecondsPerBeat;
      }
      if (isSetTempo(event)) {
        return 60_000_000 / event.microsecondsPerBeat;
      }
    }
  }
  return 120;
}

function outputFileName(inputName: string): string {
  const stem = inputName.replace(/\.[^.]+$/, '').trim() || 'midi-import';
  const cleaned = stem.replace(/[/:\\?%*"<>|]/g, '-');
  return `${cleaned}.xy`;
}

function activePatternMap(patterns: Map<number, Array<PatternNoteInput[] | null>>): TrackPatternMap {
  const out: TrackPatternMap = {};
  for (const [track, trackPatterns] of patterns) {
    if (!trackPatterns.some((pattern) => pattern && pattern.length > 0)) continue;
    out[track] = trackPatterns.map((pattern) => ({ steps: 64, notes: pattern ?? [] }));
  }
  return out;
}

function notesPerPatternByTrack(patterns: Map<number, Array<PatternNoteInput[] | null>>): Record<number, number[]> {
  const out: Record<number, number[]> = {};
  for (const [track, trackPatterns] of patterns) {
    const counts = trackPatterns.map((pattern) => pattern?.length ?? 0);
    if (counts.some((count) => count > 0)) {
      out[track] = counts;
    }
  }
  return out;
}

export function buildMidiProjectFromBytes(
  midiBytes: Uint8Array,
  fileName: string,
  baselineBytes: Uint8Array,
  options: MidiImportOptions = {},
): MidiImportResult {
  const midi = parseMidi(midiBytes);
  const ticksPerBeat = midi.header.ticksPerBeat ?? midi.header.timeDivision;
  if (!ticksPerBeat) {
    throw new Error('SMPTE-timed MIDI files are not supported yet.');
  }

  const startBar = 0;
  const laneNotes = extractMidiParts(midi);
  const numPatterns = autoDetectPatterns(laneNotes, ticksPerBeat, startBar);
  const totalBars = numPatterns * 4;
  const selection = selectBestParts(laneNotes, ticksPerBeat, startBar, totalBars);
  if (selection.assignments.size === 0) {
    throw new Error('No usable MIDI note lanes were found.');
  }

  const trackPatterns = buildTrackPatterns(selection, ticksPerBeat, startBar, numPatterns);
  const arrangementMap = activePatternMap(trackPatterns);
  if (Object.keys(arrangementMap).length === 0) {
    throw new Error('No notes remained after MIDI segmentation.');
  }

  const arrangementBytes = buildArrangementFromBytes(baselineBytes, arrangementMap);
  const imageProject = ImageProject.fromBytes(arrangementBytes);
  const bpm = options.bpmOverride ?? firstTempoBpm(midi);
  imageProject.setTempo(bpm);

  const activeTracks = Object.keys(arrangementMap).map((track) => Number(track)).sort((a, b) => a - b);
  for (let sceneIndex = 0; sceneIndex < numPatterns; sceneIndex++) {
    const row = Array(TRACK_COUNT).fill(0);
    for (const track of activeTracks) {
      row[track - 1] = Math.min(sceneIndex, imageProject.getPatternCount(track) - 1);
    }
    imageProject.setSceneRow(sceneIndex, row, Array(TRACK_COUNT).fill(false));
  }
  imageProject.setSongChain(0, Array.from({ length: numPatterns }, (_, index) => index), true);

  const summary: MidiImportSummary = {
    bpm,
    ticksPerBeat,
    patterns: numPatterns,
    totalBars,
    importedNotes: Object.values(notesPerPatternByTrack(trackPatterns)).flat().reduce((sum, count) => sum + count, 0),
    activeTracks,
    notesPerPatternByTrack: notesPerPatternByTrack(trackPatterns),
  };

  return {
    project: buildProjectViewModel(
      imageProject,
      outputFileName(fileName),
      { activeTrackIndex: Math.max(0, (activeTracks[0] ?? 1) - 1), activePatternIndex: 0, activeSceneIndex: 0 },
      true,
    ),
    summary,
  };
}

async function defaultBaselineBytes(): Promise<Uint8Array> {
  baselineBytesPromise ??= fetch(`${import.meta.env.BASE_URL}baselines/blank.xy`).then(async (response) => {
    if (!response.ok) {
      throw new Error('The built-in blank project could not be loaded.');
    }
    return new Uint8Array(await response.arrayBuffer());
  });
  return baselineBytesPromise;
}

export async function loadMidiFileAsNewProject(file: File, options: MidiImportOptions = {}): Promise<MidiImportResult> {
  const [midiBuffer, baseline] = await Promise.all([
    file.arrayBuffer(),
    defaultBaselineBytes(),
  ]);
  return buildMidiProjectFromBytes(new Uint8Array(midiBuffer), file.name, baseline, options);
}
