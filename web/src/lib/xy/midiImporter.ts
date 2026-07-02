import {
  parseMidi,
  type MidiData,
  type MidiEvent,
  type MidiNoteOffEvent,
  type MidiNoteOnEvent,
  type MidiSetTempoEvent,
} from "midi-file";
import {
  buildArrangementFromBytes,
  ImageProject,
  SCENE_COUNT,
  SONG_MAX_CHAIN,
  STEP_TICKS,
  TRACK_COUNT,
  type PatternNoteInput,
  type TrackPatternMap,
  type TrackTemplateMap,
} from "./image_writer";
import {
  buildProjectViewModel,
  type XYProjectViewModel,
} from "./projectViewModel";

export type MidiImportRole = "drum" | "bass" | "lead" | "chord";

type Role = MidiImportRole;
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

export type MidiPreviewNote = {
  id: string;
  start16ths: number;
  duration16ths: number;
  note: number;
  velocity: number;
};

export type MidiTrackSelectionOption = {
  id: LaneKey;
  midiTrackIndex: number;
  channel: number;
  name: string;
  role: MidiImportRole;
  isDrum: boolean;
  noteCount: number;
  uniquePitches: number;
  activeBars: number;
  pitchMin: number;
  pitchMax: number;
  start16ths: number;
  end16ths: number;
  uniquePatternCount: number;
  bankCount: number;
  previewNotes: MidiPreviewNote[];
};

export type MidiTrackSelectionSummary = {
  tracks: MidiTrackSelectionOption[];
  selectedTrackIds: LaneKey[];
  requiredBankCount: number;
  selectedBankCount: number;
  maxInstrumentTracks: number;
  maxPatternsPerTrack: number;
  isSelectionRecommended: boolean;
  warning: string | null;
  sourceTotalBars: number;
  sourceTotal16ths: number;
  rangeStart16ths: number;
  rangeEnd16ths: number;
  rangeWasAutoFit: boolean;
  totalBars: number;
  total16ths: number;
};

export type MidiImportSummary = {
  bpm: number;
  ticksPerBeat: number;
  /** Legacy name for the number of four-bar timeline windows. */
  patterns: number;
  scenes: number;
  totalBars: number;
  sourceTotalBars: number;
  sourceTotal16ths: number;
  rangeStart16ths: number;
  rangeEnd16ths: number;
  rangeWasAutoFit: boolean;
  importedNotes: number;
  activeTracks: number[];
  notesPerPatternByTrack: Record<number, number[]>;
  trackSelection: MidiTrackSelectionSummary | null;
};

export type MidiImportResult = {
  project: XYProjectViewModel;
  summary: MidiImportSummary;
};

export type MidiImportOptions = {
  bpmOverride?: number;
  selectedTrackIds?: string[];
  rangeStart16ths?: number;
  rangeEnd16ths?: number;
  fitToCapacity?: boolean;
};

const ROLE_SLOTS: Record<number, Role> = {
  1: "drum",
  2: "drum",
  3: "bass",
  4: "lead",
  5: "lead",
  6: "lead",
  7: "chord",
  8: "chord",
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
const MAX_PREVIEW_NOTES_PER_TRACK = 900;
const MAX_PATTERNS_PER_TRACK = 16;
const INSTRUMENT_TRACK_COUNT = 8;
const BAR_16THS = 16;
const PATTERN_16THS = BAR_16THS * 4;

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
  return event.type === "noteOn";
}

function isNoteOff(event: MidiEvent): event is MidiNoteOffEvent {
  return event.type === "noteOff";
}

function isSetTempo(event: MidiEvent): event is MidiSetTempoEvent {
  return event.type === "setTempo";
}

function laneKey(trackIndex: number, channel: number): LaneKey {
  return `${trackIndex}:${channel}`;
}

function splitLaneKey(key: LaneKey): [number, number] {
  const [track, channel] = key.split(":").map((part) => Number(part));
  return [track, channel];
}

function candidateId(candidate: PartCandidate): LaneKey {
  return laneKey(candidate.key[0], candidate.key[1]);
}

function midiTrackNames(midi: MidiData): string[] {
  return midi.tracks.map((track, index) => {
    const nameEvent = track.find(
      (event) => event.type === "trackName" && event.text.trim().length > 0,
    );
    return nameEvent?.type === "trackName"
      ? nameEvent.text.trim()
      : `MIDI track ${index + 1}`;
  });
}

function bestRole(candidate: PartCandidate): Role {
  if (candidate.isDrumChannel) return "drum";
  return (["bass", "lead", "chord"] as Role[]).reduce((best, role) =>
    candidate.roleScores[role] > candidate.roleScores[best] ? role : best,
  );
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

function selectBarWindow(
  notes: MidiNote[],
  midiTpb: number,
  startBar: number,
  numBars: number,
): MidiNote[] {
  const ticksPerBar = midiTpb * 4;
  const lo = startBar * ticksPerBar;
  const hi = (startBar + numBars) * ticksPerBar;
  return notes.filter((note) => lo <= note.absTick && note.absTick < hi);
}

function ticksPer16th(midiTpb: number): number {
  return midiTpb / 4;
}

function select16thWindow(
  notes: MidiNote[],
  midiTpb: number,
  start16ths: number,
  duration16ths: number,
): MidiNote[] {
  const tick16th = ticksPer16th(midiTpb);
  const lo = start16ths * tick16th;
  const hi = (start16ths + duration16ths) * tick16th;
  return notes.filter((note) => lo <= note.absTick && note.absTick < hi);
}

function midiSourceTotal16ths(
  laneNotes: Map<LaneKey, MidiNote[]>,
  midiTpb: number,
): number {
  const tick16th = ticksPer16th(midiTpb);
  let maxTick = 0;
  for (const notes of laneNotes.values()) {
    for (const note of notes) {
      maxTick = Math.max(maxTick, note.absTick + note.gateTicks);
    }
  }
  return Math.max(BAR_16THS, Math.ceil(maxTick / tick16th));
}

type ImportRange = {
  start16ths: number;
  end16ths: number;
  total16ths: number;
  totalBars: number;
  numPatterns: number;
};

function rangeFromPatternCount(
  start16ths: number,
  numPatterns: number,
): ImportRange {
  const total16ths = Math.max(PATTERN_16THS, numPatterns * PATTERN_16THS);
  return {
    start16ths,
    end16ths: start16ths + total16ths,
    total16ths,
    totalBars: total16ths / BAR_16THS,
    numPatterns: Math.max(1, numPatterns),
  };
}

function normalizeImportRange(
  options: MidiImportOptions,
  sourceTotal16ths: number,
): ImportRange {
  const maxPatterns = Math.min(SCENE_COUNT, SONG_MAX_CHAIN);
  const sourceEnd = Math.max(BAR_16THS, sourceTotal16ths);
  const start16ths = Math.max(
    0,
    Math.min(sourceEnd - 1, Math.round(options.rangeStart16ths ?? 0)),
  );
  const requestedEnd = Math.max(
    start16ths + BAR_16THS,
    Math.min(sourceEnd, Math.round(options.rangeEnd16ths ?? sourceEnd)),
  );
  const requestedPatterns = Math.ceil(
    (requestedEnd - start16ths) / PATTERN_16THS,
  );
  const availablePatterns = Math.max(
    1,
    Math.ceil((sourceEnd - start16ths) / PATTERN_16THS),
  );
  return rangeFromPatternCount(
    start16ths,
    Math.min(requestedPatterns, availablePatterns, maxPatterns),
  );
}

function partFingerprint(
  notesWindow: MidiNote[],
  midiTpb: number,
  start16ths: number,
  isDrumChannel: boolean,
): Set<string> {
  const sig = new Set<string>();
  if (notesWindow.length === 0) return sig;

  const lo = start16ths * ticksPer16th(midiTpb);
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
  lead +=
    52 <= meanPitch && meanPitch <= 90 ? 10 : -Math.abs(meanPitch - 71) * 0.55;
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
  start16ths: number,
  total16ths: number,
): PartCandidate[] {
  const totalBars = Math.max(1, Math.ceil(total16ths / BAR_16THS));
  const tick16th = ticksPer16th(midiTpb);
  const lo = start16ths * tick16th;
  const candidates: PartCandidate[] = [];

  for (const [key, notesAll] of laneNotes) {
    const notesWindow = select16thWindow(
      notesAll,
      midiTpb,
      start16ths,
      total16ths,
    );
    if (notesWindow.length < 3) continue;

    const pitches = notesWindow.map((note) => note.note);
    const noteCount = notesWindow.length;
    const uniquePitches = new Set(pitches).size;
    const pitchMin = Math.min(...pitches);
    const pitchMax = Math.max(...pitches);
    const meanPitch =
      pitches.reduce((sum, pitch) => sum + pitch, 0) / noteCount;
    const pitchSpan = pitchMax - pitchMin;
    const bars = new Set<number>();
    for (const note of notesWindow) {
      const bar = Math.max(
        0,
        Math.min(
          totalBars - 1,
          Math.floor((note.absTick - lo) / (tick16th * BAR_16THS)),
        ),
      );
      bars.add(bar);
    }

    const onsetCounts = new Map<number, number>();
    for (const note of notesWindow) {
      onsetCounts.set(note.absTick, (onsetCounts.get(note.absTick) ?? 0) + 1);
    }
    const chordOnsets = Array.from(onsetCounts.values()).filter(
      (count) => count > 1,
    ).length;
    const polyphonyRatio = chordOnsets / Math.max(1, onsetCounts.size);
    const avgNotesPerOnset = noteCount / Math.max(1, onsetCounts.size);

    const [, channel] = splitLaneKey(key);
    const isDrumChannel = channel === 9;
    const drumNoteHits = pitches.filter(
      (pitch) => 27 <= pitch && pitch <= 87,
    ).length;
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
      fingerprint: partFingerprint(
        notesWindow,
        midiTpb,
        start16ths,
        isDrumChannel,
      ),
    });
  }

  candidates.sort(
    (a, b) =>
      b.utilityScore - a.utilityScore ||
      b.noteCount - a.noteCount ||
      b.activeBars - a.activeBars,
  );
  return candidates;
}

function dedupeCandidates(
  candidates: PartCandidate[],
): [PartCandidate[], Array<[PartCandidate, PartCandidate, number]>] {
  const kept: PartCandidate[] = [];
  const dropped: Array<[PartCandidate, PartCandidate, number]> = [];

  for (const candidate of candidates) {
    let duplicateOf: PartCandidate | undefined;
    let duplicateSimilarity = 0;
    for (const ref of kept) {
      if (candidate.isDrumChannel !== ref.isDrumChannel) continue;
      const similarity = jaccardSimilarity(
        candidate.fingerprint,
        ref.fingerprint,
      );
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

function roleCandidateOk(
  candidate: PartCandidate,
  role: Role,
  totalBars: number,
  relaxed = false,
): boolean {
  let minNotes = ROLE_MIN_NOTES[role];
  let minBars = ROLE_MIN_ACTIVE_BARS[role];
  if (relaxed) {
    minNotes = Math.max(6, Math.floor(minNotes / 2));
    minBars = Math.max(1, minBars - 1);
  }
  if (candidate.noteCount < minNotes || candidate.activeBars < minBars)
    return false;

  if (role === "drum") {
    if (candidate.isDrumChannel) return true;
    if (!relaxed) return false;
    return (
      candidate.roleScores.drum >= ROLE_MIN_SCORE.drum * 0.7 &&
      candidate.polyphonyRatio <= 0.08 &&
      candidate.meanPitch <= 58 &&
      candidate.pitchMax - candidate.pitchMin <= 20
    );
  }
  if (role === "bass") {
    if (candidate.isDrumChannel) return false;
    return (
      candidate.meanPitch <= 62 &&
      candidate.polyphonyRatio <= (relaxed ? 0.3 : 0.2)
    );
  }
  if (role === "lead") {
    if (candidate.isDrumChannel) return false;
    return (
      candidate.meanPitch >= (relaxed ? 45 : 50) && candidate.pitchMax >= 55
    );
  }
  if (candidate.isDrumChannel) return false;
  const minPoly = relaxed ? 0.12 : 0.2;
  const minOnsetStack = relaxed ? 1.25 : 1.35;
  const minCoverage = Math.max(
    2,
    Math.round(totalBars * (relaxed ? 0.12 : 0.18)),
  );
  return (
    (candidate.polyphonyRatio >= minPoly ||
      candidate.avgNotesPerOnset >= minOnsetStack) &&
    candidate.activeBars >= minCoverage
  );
}

function assignPartsToSlots(
  candidates: PartCandidate[],
  totalBars: number,
): Map<number, PartCandidate> {
  const remaining = [...candidates];
  const assignments = new Map<number, PartCandidate>();

  if (remaining.length === 1) {
    const candidate = remaining[0];
    if (candidate.isDrumChannel) {
      assignments.set(1, candidate);
      return assignments;
    }
    const roles: Role[] = ["bass", "lead", "chord"];
    const eligible = roles.filter((role) =>
      roleCandidateOk(candidate, role, totalBars, true),
    );
    const role = (eligible.length ? eligible : roles).reduce(
      (best, roleName) =>
        candidate.roleScores[roleName] > candidate.roleScores[best]
          ? roleName
          : best,
    );
    assignments.set(SINGLE_ROLE_SLOT[role], candidate);
    return assignments;
  }

  function pickForRole(role: Role, relaxed = false): PartCandidate | undefined {
    const pool = remaining.filter((candidate) =>
      roleCandidateOk(candidate, role, totalBars, relaxed),
    );
    if (pool.length === 0) return undefined;
    pool.sort(
      (a, b) =>
        b.roleScores[role] - a.roleScores[role] ||
        b.utilityScore - a.utilityScore ||
        b.noteCount - a.noteCount ||
        a.key[0] - b.key[0] ||
        a.key[1] - b.key[1],
    );
    const best = pool[0];
    if (best.roleScores[role] < ROLE_MIN_SCORE[role] * (relaxed ? 0.75 : 1))
      return undefined;
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
    remaining.sort(
      (a, b) =>
        b.roleScores.lead - a.roleScores.lead ||
        b.utilityScore - a.utilityScore ||
        b.noteCount - a.noteCount ||
        b.activeBars - a.activeBars,
    );
    const best = remaining[0];
    if (best.utilityScore < 8) continue;
    remaining.shift();
    assignments.set(slot, best);
  }

  return assignments;
}

function assignSelectedPartsToSlots(
  candidates: PartCandidate[],
): Map<number, PartCandidate> {
  const assignments = new Map<number, PartCandidate>();
  const openSlots = new Set(
    Array.from({ length: INSTRUMENT_TRACK_COUNT }, (_, index) => index + 1),
  );
  const preferredSlots: Record<Role, number[]> = {
    drum: [1, 2],
    bass: [3],
    lead: [4, 5, 6],
    chord: [7, 8],
  };
  const melodicSlots = [3, 4, 5, 6, 7, 8];

  function takeSlot(candidate: PartCandidate): number | undefined {
    const role = bestRole(candidate);
    const slotOrder = [
      ...preferredSlots[role],
      ...(candidate.isDrumChannel ? [] : melodicSlots),
      ...Array.from(
        { length: INSTRUMENT_TRACK_COUNT },
        (_, index) => index + 1,
      ),
    ];
    for (const slot of slotOrder) {
      if (!openSlots.has(slot)) continue;
      openSlots.delete(slot);
      return slot;
    }
    return undefined;
  }

  for (const candidate of candidates) {
    const slot = takeSlot(candidate);
    if (slot === undefined) break;
    assignments.set(slot, candidate);
  }

  return assignments;
}

function selectBestParts(
  laneNotes: Map<LaneKey, MidiNote[]>,
  midiTpb: number,
  start16ths: number,
  total16ths: number,
): SelectionResult {
  const candidates = buildPartCandidates(
    laneNotes,
    midiTpb,
    start16ths,
    total16ths,
  );
  const [rankedParts, droppedDuplicates] = dedupeCandidates(candidates);
  return {
    assignments: assignPartsToSlots(
      rankedParts,
      Math.max(1, Math.ceil(total16ths / BAR_16THS)),
    ),
    rankedParts,
    droppedDuplicates,
  };
}

function midiToXyNotes(
  midiNotes: MidiNote[],
  midiTpb: number,
  start16ths: number,
  isDrum: boolean,
): PatternNoteInput[] {
  const tickOffsetMidi = start16ths * ticksPer16th(midiTpb);
  const scale = 1920 / midiTpb;
  const xyNotes: PatternNoteInput[] = [];

  for (const note of midiNotes) {
    const midiTickInPattern = note.absTick - tickOffsetMidi;
    let xyTick = Math.round(midiTickInPattern * scale);
    xyTick = Math.round(xyTick / STEP_TICKS) * STEP_TICKS;
    const step0 = Math.floor(xyTick / STEP_TICKS);
    const step = step0 + 1;
    const tickOffset = xyTick % STEP_TICKS;
    if (step < 1 || step > 64) continue;

    let gateTicks = Math.round(note.gateTicks * scale);
    gateTicks = Math.max(
      STEP_TICKS,
      Math.round(gateTicks / STEP_TICKS) * STEP_TICKS,
    );
    xyNotes.push({
      step,
      note: isDrum ? remapDrumNote(note.note) : note.note,
      velocity: Math.max(1, Math.min(127, note.velocity)),
      tickOffset,
      gateTicks,
    });
  }

  xyNotes.sort(
    (a, b) =>
      (a.step - 1) * STEP_TICKS +
      (a.tickOffset ?? 0) -
      ((b.step - 1) * STEP_TICKS + (b.tickOffset ?? 0)),
  );
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
    const group = [...(byOnset.get(onset) ?? [])].sort(
      (a, b) => a.note - b.note,
    );
    if (group.length >= 2) {
      upperVoices.push(
        ...group.slice(-Math.max(1, Math.floor(group.length / 2))),
      );
    }
  }
  if (upperVoices.length > 0) return upperVoices;

  const pitches = notesWindow.map((note) => note.note).sort((a, b) => a - b);
  const median = pitches[Math.floor(pitches.length / 2)];
  const highNotes = notesWindow.filter((note) => note.note >= median);
  if (highNotes.length > 0) return highNotes;
  return (
    notesWindow.filter((_, index) => index % 2 === 1) || notesWindow.slice(0, 1)
  );
}

function buildTrackPatterns(
  selection: SelectionResult,
  midiTpb: number,
  start16ths: number,
  numPatterns: number,
  includeDerivedParts = true,
): Map<number, Array<PatternNoteInput[] | null>> {
  const trackPatterns = new Map<number, Array<PatternNoteInput[] | null>>();
  const drumPrimary =
    selection.assignments.get(1) ?? selection.assignments.get(2);
  const chordPrimary =
    selection.assignments.get(7) ?? selection.assignments.get(8);
  const deriveMissingRoles =
    new Set(
      Array.from(selection.assignments.values()).map((candidate) =>
        candidate.key.join(":"),
      ),
    ).size > 1;

  for (let slot = 1; slot <= 8; slot++) {
    const role = ROLE_SLOTS[slot];
    const candidate = selection.assignments.get(slot);
    const patterns: Array<PatternNoteInput[] | null> = [];

    for (let patternIndex = 0; patternIndex < numPatterns; patternIndex++) {
      const patternStart16ths = start16ths + patternIndex * PATTERN_16THS;
      let sourceNotes: MidiNote[] = [];
      if (candidate) {
        sourceNotes = select16thWindow(
          candidate.notesAll,
          midiTpb,
          patternStart16ths,
          PATTERN_16THS,
        );
      } else if (
        includeDerivedParts &&
        role === "drum" &&
        drumPrimary &&
        deriveMissingRoles
      ) {
        const base = select16thWindow(
          drumPrimary.notesAll,
          midiTpb,
          patternStart16ths,
          PATTERN_16THS,
        );
        sourceNotes = deriveSecondaryDrumWindow(base);
      } else if (
        includeDerivedParts &&
        role === "chord" &&
        chordPrimary &&
        deriveMissingRoles
      ) {
        const base = select16thWindow(
          chordPrimary.notesAll,
          midiTpb,
          patternStart16ths,
          PATTERN_16THS,
        );
        sourceNotes = deriveSecondaryChordWindow(base);
      }

      const xyNotes =
        sourceNotes.length > 0
          ? midiToXyNotes(
              sourceNotes,
              midiTpb,
              patternStart16ths,
              role === "drum",
            )
          : [];
      patterns.push(
        xyNotes.length > 0 ? xyNotes.slice(0, MAX_NOTES_PER_PATTERN) : null,
      );
    }
    trackPatterns.set(slot, patterns);
  }

  return trackPatterns;
}

function autoDetectPatterns(
  laneNotes: Map<LaneKey, MidiNote[]>,
  midiTpb: number,
  startBar: number,
): number {
  const ticksPerBar = midiTpb * 4;
  let maxTick = 0;
  for (const notes of laneNotes.values()) {
    for (const note of notes) {
      maxTick = Math.max(maxTick, note.absTick + note.gateTicks);
    }
  }
  const totalBars = Math.max(1, Math.ceil(maxTick / ticksPerBar));
  const remainingBars = Math.max(1, totalBars - startBar);
  return Math.max(1, Math.ceil(remainingBars / 4));
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
  const stem = midiProjectStem(inputName);
  return `${stem}.xy`;
}

function midiProjectStem(inputName: string): string {
  const withoutExtension = inputName.replace(/\.[^.]+$/, "").trim();
  const withoutCredits = withoutExtension
    .replace(/\s*[\[(][^\])]*[\])]\s*/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  let parts = withoutCredits
    .split(/\s+[-–—]\s+/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length > 1 && /^\d+([._\s-]\d+)?$/.test(parts[0])) {
    parts = parts.slice(1);
  }

  const title = parts.length > 1 ? parts.slice(1).join(" ") : parts[0];
  const cleaned =
    (title || withoutCredits || "midi")
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/&/g, "and")
      .replace(/[^a-z0-9]/g, "")
      .slice(0, 16) || "midi";

  return cleaned;
}

type BankedArrangement = {
  trackPatterns: TrackPatternMap;
  trackTemplates: TrackTemplateMap;
  sceneRows: number[][];
  sceneMutes: boolean[][];
  activeTracks: number[];
};

type SourcePatternBank = {
  sourceTrack: number;
  uniquePatterns: PatternNoteInput[][];
  windowPatternIndexes: Array<number | null>;
  hosts: number[];
};

function patternSignature(pattern: PatternNoteInput[]): string {
  return pattern
    .map((note) => {
      const tickOffset = note.tickOffset ?? note.tick_offset ?? 0;
      const gateTicks = note.gateTicks ?? note.gate_ticks ?? 240;
      return [
        note.step,
        note.note,
        note.velocity ?? 100,
        tickOffset,
        gateTicks,
      ].join(":");
    })
    .join("|");
}

function candidatePatternBankCost(
  candidate: PartCandidate,
  midiTpb: number,
  start16ths: number,
  numPatterns: number,
): Pick<MidiTrackSelectionOption, "uniquePatternCount" | "bankCount"> {
  const uniqueSignatures = new Set<string>();

  for (let patternIndex = 0; patternIndex < numPatterns; patternIndex++) {
    const patternStart16ths = start16ths + patternIndex * PATTERN_16THS;
    const sourceNotes = select16thWindow(
      candidate.notesAll,
      midiTpb,
      patternStart16ths,
      PATTERN_16THS,
    );
    const xyNotes =
      sourceNotes.length > 0
        ? midiToXyNotes(
            sourceNotes,
            midiTpb,
            patternStart16ths,
            candidate.isDrumChannel,
          ).slice(0, MAX_NOTES_PER_PATTERN)
        : [];
    if (xyNotes.length > 0) uniqueSignatures.add(patternSignature(xyNotes));
  }

  const uniquePatternCount = uniqueSignatures.size;
  return {
    uniquePatternCount,
    bankCount: Math.ceil(uniquePatternCount / MAX_PATTERNS_PER_TRACK),
  };
}

function candidatePreviewNotes(
  candidate: PartCandidate,
  midiTpb: number,
): MidiPreviewNote[] {
  const tick16th = ticksPer16th(midiTpb);
  const stride = Math.max(
    1,
    Math.ceil(candidate.notesWindow.length / MAX_PREVIEW_NOTES_PER_TRACK),
  );
  const notes: MidiPreviewNote[] = [];

  for (let index = 0; index < candidate.notesWindow.length; index += stride) {
    const note = candidate.notesWindow[index];
    notes.push({
      id: `${candidateId(candidate)}:${index}`,
      start16ths: Math.max(0, note.absTick / tick16th),
      duration16ths: Math.max(0.125, note.gateTicks / tick16th),
      note: candidate.isDrumChannel ? remapDrumNote(note.note) : note.note,
      velocity: note.velocity,
    });
  }

  return notes;
}

function buildTrackSelectionOption(
  candidate: PartCandidate,
  trackNames: string[],
  midiTpb: number,
  start16ths: number,
  numPatterns: number,
): MidiTrackSelectionOption {
  const id = candidateId(candidate);
  const [midiTrackIndex, midiChannel] = candidate.key;
  const baseName =
    trackNames[midiTrackIndex] ?? `MIDI track ${midiTrackIndex + 1}`;
  const displayName =
    baseName.trim().length > 0
      ? baseName.trim()
      : `MIDI track ${midiTrackIndex + 1}`;
  const previewNotes = candidatePreviewNotes(candidate, midiTpb);
  const trackStart16ths =
    previewNotes.length > 0
      ? Math.min(...previewNotes.map((note) => note.start16ths))
      : 0;
  const end16ths =
    previewNotes.length > 0
      ? Math.max(
          ...previewNotes.map((note) => note.start16ths + note.duration16ths),
        )
      : trackStart16ths + 1;

  return {
    id,
    midiTrackIndex,
    channel: midiChannel + 1,
    name: displayName,
    role: bestRole(candidate),
    isDrum: candidate.isDrumChannel,
    noteCount: candidate.noteCount,
    uniquePitches: candidate.uniquePitches,
    activeBars: candidate.activeBars,
    pitchMin: candidate.pitchMin,
    pitchMax: candidate.pitchMax,
    start16ths: trackStart16ths,
    end16ths,
    ...candidatePatternBankCost(candidate, midiTpb, start16ths, numPatterns),
    previewNotes,
  };
}

function bankLimitWarning(requiredBankCount: number): string {
  return `OP-XY has ${INSTRUMENT_TRACK_COUNT} instrument tracks - which tracks will you pick?!.`;
}

function buildTrackSelectionSummary(args: {
  options: MidiTrackSelectionOption[];
  selectedTrackIds: LaneKey[];
  sourceTotal16ths: number;
  range: ImportRange;
  rangeWasAutoFit: boolean;
  totalBars: number;
}): MidiTrackSelectionSummary | null {
  const {
    options,
    selectedTrackIds,
    sourceTotal16ths,
    range,
    rangeWasAutoFit,
    totalBars,
  } = args;
  if (options.length === 0) return null;

  const selected = new Set(selectedTrackIds);
  const requiredBankCount = options.reduce(
    (sum, option) => sum + option.bankCount,
    0,
  );
  const selectedBankCount = options.reduce(
    (sum, option) => sum + (selected.has(option.id) ? option.bankCount : 0),
    0,
  );
  const isSelectionRecommended =
    requiredBankCount > INSTRUMENT_TRACK_COUNT ||
    options.length > INSTRUMENT_TRACK_COUNT;

  return {
    tracks: options,
    selectedTrackIds,
    requiredBankCount,
    selectedBankCount,
    maxInstrumentTracks: INSTRUMENT_TRACK_COUNT,
    maxPatternsPerTrack: MAX_PATTERNS_PER_TRACK,
    isSelectionRecommended,
    warning: isSelectionRecommended
      ? bankLimitWarning(requiredBankCount)
      : null,
    sourceTotalBars: Math.max(1, Math.ceil(sourceTotal16ths / BAR_16THS)),
    sourceTotal16ths,
    rangeStart16ths: range.start16ths,
    rangeEnd16ths: range.end16ths,
    rangeWasAutoFit,
    totalBars,
    total16ths: totalBars * BAR_16THS,
  };
}

function selectedCandidateList(
  rankedParts: PartCandidate[],
  selectedTrackIds: string[],
): PartCandidate[] {
  const selectedOrder = new Map(
    selectedTrackIds.map((id, index) => [id, index] as const),
  );
  return rankedParts
    .filter((candidate) => selectedOrder.has(candidateId(candidate)))
    .sort(
      (a, b) =>
        (selectedOrder.get(candidateId(a)) ?? 0) -
        (selectedOrder.get(candidateId(b)) ?? 0),
    );
}

function defaultSelectedTrackIds(
  rankedParts: PartCandidate[],
  optionsById: Map<LaneKey, MidiTrackSelectionOption>,
): LaneKey[] {
  const selected: LaneKey[] = [];
  let bankCount = 0;

  for (const candidate of rankedParts) {
    const id = candidateId(candidate);
    const option = optionsById.get(id);
    if (!option) continue;
    if (selected.length >= INSTRUMENT_TRACK_COUNT) continue;
    if (bankCount + option.bankCount > INSTRUMENT_TRACK_COUNT) continue;
    selected.push(id);
    bankCount += option.bankCount;
  }

  return selected;
}

function bankCountForSelectedCandidates(args: {
  candidates: PartCandidate[];
  selectedTrackIds: readonly string[];
  midiTpb: number;
  start16ths: number;
  numPatterns: number;
}): number {
  const selected = new Set(args.selectedTrackIds);
  return args.candidates.reduce((sum, candidate) => {
    if (!selected.has(candidateId(candidate))) return sum;
    return (
      sum +
      candidatePatternBankCost(
        candidate,
        args.midiTpb,
        args.start16ths,
        args.numPatterns,
      ).bankCount
    );
  }, 0);
}

function maxSafeRangeForSelected(args: {
  candidates: PartCandidate[];
  selectedTrackIds: readonly string[];
  midiTpb: number;
  start16ths: number;
  sourceTotal16ths: number;
}): ImportRange | null {
  const maxPatterns = Math.min(
    SCENE_COUNT,
    SONG_MAX_CHAIN,
    Math.max(
      1,
      Math.ceil((args.sourceTotal16ths - args.start16ths) / PATTERN_16THS),
    ),
  );
  let lastSafe: ImportRange | null = null;

  for (let numPatterns = 1; numPatterns <= maxPatterns; numPatterns += 1) {
    const bankCount = bankCountForSelectedCandidates({
      candidates: args.candidates,
      selectedTrackIds: args.selectedTrackIds,
      midiTpb: args.midiTpb,
      start16ths: args.start16ths,
      numPatterns,
    });
    if (bankCount > INSTRUMENT_TRACK_COUNT) break;
    lastSafe = rangeFromPatternCount(args.start16ths, numPatterns);
  }

  return lastSafe;
}

/**
 * Convert a timeline of 4-bar windows into device-valid pattern banks.
 *
 * OP-XY exposes only nine patterns on each instrument track, but Song mode
 * can chain 96 scenes. Repeated windows are stored once and selected again
 * by later scenes. A source lane with more than nine distinct windows is
 * spread over spare instrument tracks; the scene mutes every non-selected
 * bank so only one copy of that lane plays at a time.
 */
function bankTrackPatterns(
  patterns: Map<number, Array<PatternNoteInput[] | null>>,
  sceneCount: number,
): BankedArrangement {
  const sources: SourcePatternBank[] = [];

  for (const [sourceTrack, windows] of Array.from(patterns.entries()).sort(
    ([a], [b]) => a - b,
  )) {
    const uniqueBySignature = new Map<string, number>();
    const uniquePatterns: PatternNoteInput[][] = [];
    const windowPatternIndexes: Array<number | null> = [];

    for (const window of windows) {
      if (!window || window.length === 0) {
        windowPatternIndexes.push(null);
        continue;
      }
      const key = patternSignature(window);
      let patternIndex = uniqueBySignature.get(key);
      if (patternIndex === undefined) {
        patternIndex = uniquePatterns.length;
        uniqueBySignature.set(key, patternIndex);
        uniquePatterns.push(window);
      }
      windowPatternIndexes.push(patternIndex);
    }

    if (uniquePatterns.length > 0) {
      sources.push({
        sourceTrack,
        uniquePatterns,
        windowPatternIndexes,
        hosts: [],
      });
    }
  }

  if (sources.length === 0) {
    throw new Error("No notes remained after MIDI segmentation.");
  }

  const requiredTracks = sources.reduce(
    (total, source) =>
      total + Math.ceil(source.uniquePatterns.length / MAX_PATTERNS_PER_TRACK),
    0,
  );
  if (requiredTracks > INSTRUMENT_TRACK_COUNT) {
    throw new Error(
      `This MIDI needs ${requiredTracks} instrument pattern banks after reusing identical 4-bar sections; OP-XY has ${INSTRUMENT_TRACK_COUNT} instrument tracks with ${MAX_PATTERNS_PER_TRACK} patterns each. Simplify source lanes or import a shorter range.`,
    );
  }

  const reservedTracks = new Set(sources.map((source) => source.sourceTrack));
  const freeTracks = Array.from(
    { length: INSTRUMENT_TRACK_COUNT },
    (_, index) => index + 1,
  ).filter((track) => !reservedTracks.has(track));
  const out: TrackPatternMap = {};
  const trackTemplates: TrackTemplateMap = {};

  for (const source of sources) {
    const bankCount = Math.ceil(
      source.uniquePatterns.length / MAX_PATTERNS_PER_TRACK,
    );
    source.hosts = [source.sourceTrack];
    while (source.hosts.length < bankCount) {
      const host = freeTracks.shift();
      if (host === undefined) {
        throw new Error("Could not allocate an instrument pattern bank.");
      }
      source.hosts.push(host);
    }

    source.hosts.forEach((host, bankIndex) => {
      const begin = bankIndex * MAX_PATTERNS_PER_TRACK;
      const bank = source.uniquePatterns.slice(
        begin,
        begin + MAX_PATTERNS_PER_TRACK,
      );
      out[host] = bank.map((notes) => ({ steps: 64, notes }));
      trackTemplates[host] = source.sourceTrack;
    });
  }

  const sceneRows = Array.from({ length: sceneCount }, () =>
    Array(TRACK_COUNT).fill(0),
  );
  const sceneMutes = Array.from({ length: sceneCount }, () =>
    Array(TRACK_COUNT).fill(false),
  );
  for (const source of sources) {
    for (let sceneIndex = 0; sceneIndex < sceneCount; sceneIndex++) {
      for (const host of source.hosts) {
        sceneMutes[sceneIndex][host - 1] = true;
      }
      const uniquePatternIndex = source.windowPatternIndexes[sceneIndex];
      if (uniquePatternIndex === null || uniquePatternIndex === undefined) {
        continue;
      }
      const bankIndex = Math.floor(uniquePatternIndex / MAX_PATTERNS_PER_TRACK);
      const host = source.hosts[bankIndex];
      sceneRows[sceneIndex][host - 1] =
        uniquePatternIndex % MAX_PATTERNS_PER_TRACK;
      sceneMutes[sceneIndex][host - 1] = false;
    }
  }

  return {
    trackPatterns: out,
    trackTemplates,
    sceneRows,
    sceneMutes,
    activeTracks: Object.keys(out)
      .map((track) => Number(track))
      .sort((a, b) => a - b),
  };
}

function notesPerPatternByTrack(
  patterns: Map<number, Array<PatternNoteInput[] | null>>,
): Record<number, number[]> {
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
    throw new Error("SMPTE-timed MIDI files are not supported yet.");
  }
  const midiTpb = ticksPerBeat;

  const laneNotes = extractMidiParts(midi);
  const trackNames = midiTrackNames(midi);
  const sourceTotal16ths = midiSourceTotal16ths(laneNotes, midiTpb);
  let range = normalizeImportRange(options, sourceTotal16ths);
  let rangeWasAutoFit = false;

  function buildSelectionForRange(currentRange: ImportRange) {
    const fullSelection = selectBestParts(
      laneNotes,
      midiTpb,
      currentRange.start16ths,
      currentRange.total16ths,
    );
    const trackOptions = fullSelection.rankedParts
      .map((candidate) =>
        buildTrackSelectionOption(
          candidate,
          trackNames,
          midiTpb,
          currentRange.start16ths,
          currentRange.numPatterns,
        ),
      )
      .sort(
        (a, b) =>
          a.midiTrackIndex - b.midiTrackIndex ||
          a.channel - b.channel ||
          b.noteCount - a.noteCount,
      );
    const optionsById = new Map(
      trackOptions.map((option) => [option.id, option]),
    );
    const requiredBankCount = trackOptions.reduce(
      (sum, option) => sum + option.bankCount,
      0,
    );
    return { fullSelection, trackOptions, optionsById, requiredBankCount };
  }

  let rangeSelection = buildSelectionForRange(range);
  const shouldUseExplicitSelection =
    options.selectedTrackIds !== undefined ||
    rangeSelection.requiredBankCount > INSTRUMENT_TRACK_COUNT ||
    rangeSelection.trackOptions.length > INSTRUMENT_TRACK_COUNT;

  let selection = rangeSelection.fullSelection;
  let includeDerivedParts = true;
  let selectedTrackIds: LaneKey[] = Array.from(
    new Set(
      Array.from(rangeSelection.fullSelection.assignments.values()).map(
        (candidate) => candidateId(candidate),
      ),
    ),
  );

  if (shouldUseExplicitSelection) {
    selectedTrackIds =
      options.selectedTrackIds === undefined
        ? defaultSelectedTrackIds(
            rangeSelection.fullSelection.rankedParts,
            rangeSelection.optionsById,
          )
        : options.selectedTrackIds.filter((id): id is LaneKey =>
            rangeSelection.optionsById.has(id as LaneKey),
          );
    let selectedBankCount = selectedTrackIds.reduce(
      (sum, id) => sum + (rangeSelection.optionsById.get(id)?.bankCount ?? 0),
      0,
    );
    if (
      selectedBankCount > INSTRUMENT_TRACK_COUNT &&
      options.fitToCapacity &&
      selectedTrackIds.length <= INSTRUMENT_TRACK_COUNT
    ) {
      const safeRange = maxSafeRangeForSelected({
        candidates: rangeSelection.fullSelection.rankedParts,
        selectedTrackIds,
        midiTpb,
        start16ths: range.start16ths,
        sourceTotal16ths,
      });
      if (safeRange) {
        range = safeRange;
        rangeWasAutoFit = true;
        rangeSelection = buildSelectionForRange(range);
        selectedTrackIds = selectedTrackIds.filter((id): id is LaneKey =>
          rangeSelection.optionsById.has(id as LaneKey),
        );
        selectedBankCount = selectedTrackIds.reduce(
          (sum, id) =>
            sum + (rangeSelection.optionsById.get(id)?.bankCount ?? 0),
          0,
        );
      }
    }

    if (
      selectedTrackIds.length > INSTRUMENT_TRACK_COUNT ||
      selectedBankCount > INSTRUMENT_TRACK_COUNT
    ) {
      throw new Error(
        `Selected MIDI tracks need ${selectedBankCount} OP-XY instrument pattern banks; choose ${INSTRUMENT_TRACK_COUNT} or fewer.`,
      );
    }

    const selectedCandidates = selectedCandidateList(
      rangeSelection.fullSelection.rankedParts,
      selectedTrackIds,
    );
    selection = {
      ...rangeSelection.fullSelection,
      assignments: assignSelectedPartsToSlots(selectedCandidates),
      rankedParts: selectedCandidates,
    };
    includeDerivedParts = false;
  }

  if (selection.assignments.size === 0) {
    throw new Error("No usable MIDI note lanes were found.");
  }

  let trackPatterns = buildTrackPatterns(
    selection,
    midiTpb,
    range.start16ths,
    range.numPatterns,
    includeDerivedParts,
  );
  let banked: BankedArrangement;
  try {
    banked = bankTrackPatterns(trackPatterns, range.numPatterns);
  } catch (error) {
    // Secondary drum/chord parts are generated conveniences, not source MIDI.
    // Prefer the complete source timeline when those extras would consume the
    // final instrument bank needed by a long arrangement.
    if (!includeDerivedParts) throw error;
    const sourceOnlyPatterns = buildTrackPatterns(
      selection,
      midiTpb,
      range.start16ths,
      range.numPatterns,
      false,
    );
    try {
      banked = bankTrackPatterns(sourceOnlyPatterns, range.numPatterns);
      trackPatterns = sourceOnlyPatterns;
    } catch {
      throw error;
    }
  }

  const arrangementBytes = buildArrangementFromBytes(
    baselineBytes,
    banked.trackPatterns,
    banked.trackTemplates,
  );
  const imageProject = ImageProject.fromBytes(arrangementBytes);
  const bpm = options.bpmOverride ?? firstTempoBpm(midi);
  imageProject.setTempo(bpm);

  const activeTracks = banked.activeTracks;
  for (let sceneIndex = 0; sceneIndex < range.numPatterns; sceneIndex++) {
    imageProject.setSceneRow(
      sceneIndex,
      banked.sceneRows[sceneIndex],
      banked.sceneMutes[sceneIndex],
    );
  }
  imageProject.setSongChain(
    0,
    Array.from({ length: range.numPatterns }, (_, index) => index),
    true,
  );

  const summary: MidiImportSummary = {
    bpm,
    ticksPerBeat: midiTpb,
    patterns: range.numPatterns,
    scenes: range.numPatterns,
    totalBars: range.totalBars,
    sourceTotalBars: Math.max(1, Math.ceil(sourceTotal16ths / BAR_16THS)),
    sourceTotal16ths,
    rangeStart16ths: range.start16ths,
    rangeEnd16ths: range.end16ths,
    rangeWasAutoFit,
    importedNotes: Object.values(notesPerPatternByTrack(trackPatterns))
      .flat()
      .reduce((sum, count) => sum + count, 0),
    activeTracks,
    notesPerPatternByTrack: notesPerPatternByTrack(trackPatterns),
    trackSelection: buildTrackSelectionSummary({
      options: rangeSelection.trackOptions,
      selectedTrackIds,
      sourceTotal16ths,
      range,
      rangeWasAutoFit,
      totalBars: range.totalBars,
    }),
  };

  return {
    project: buildProjectViewModel(
      imageProject,
      outputFileName(fileName),
      {
        activeTrackIndex: Math.max(0, (activeTracks[0] ?? 1) - 1),
        activePatternIndex: 0,
        activeSceneIndex: 0,
      },
      true,
    ),
    summary,
  };
}

async function defaultBaselineBytes(): Promise<Uint8Array> {
  baselineBytesPromise ??= fetch(
    `${import.meta.env.BASE_URL}baselines/blank.xy`,
  ).then(async (response) => {
    if (!response.ok) {
      throw new Error("The built-in blank project could not be loaded.");
    }
    return new Uint8Array(await response.arrayBuffer());
  });
  return baselineBytesPromise;
}

export async function loadMidiFileAsNewProject(
  file: File,
  options: MidiImportOptions = {},
): Promise<MidiImportResult> {
  const [midiBuffer, baseline] = await Promise.all([
    file.arrayBuffer(),
    defaultBaselineBytes(),
  ]);
  return buildMidiProjectFromBytes(
    new Uint8Array(midiBuffer),
    file.name,
    baseline,
    options,
  );
}
