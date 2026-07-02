import { decodeProject, encodeProject } from "./rle";

export const TRACK_BASE0 = 0x0d79;
export const TRACK_STRIDE = 17876;
export const TRACK_COUNT = 16;

export const OFF_PATTERN_STEPS = 0x01;
export const OFF_BARS = OFF_PATTERN_STEPS;
export const OFF_SCALE = 0x06;
export const OFF_QUANTIZATION = 0x07;
export const OFF_TRACK_GROOVE = 0x08;
export const OFF_PRISTINE = 0x11;
export const OFF_PLOCK_SHAPE = 0x3056;
export const OFF_NOTE_COUNT = 0x456f;
export const NOTE_SIZE = 12;
export const STEP_TICKS = 480;

export const GLOBAL_TEMPO = 0x00;

export const SCENE_SLOT0 = 0x95;
export const SCENE_SLOT_SIZE = 33;
export const SCENE_MUTE_VALUE = 2;
export const SCENE_COUNT = 99;
export const SONG_FOOTER_SLOTS = 14;
export const SONG_DEFAULT_SLOT_SIZE = 4;
export const SONG_MAX_CHAIN = 96;

const TRACK_HEADER_MAGIC = [0xff, 0x00, 0xfc, 0x00];
const TRACK_TO_SCENE_SLOT_DELTA = TRACK_BASE0 - SCENE_SLOT0;

export type PatternNoteInput = {
  step: number;
  note: number;
  velocity?: number;
  tickOffset?: number;
  tick_offset?: number;
  gateTicks?: number;
  gate_ticks?: number;
};

export type ArrangementPatternInput =
  | PatternNoteInput[]
  | {
      notes?: PatternNoteInput[];
      steps?: number;
      bars?: number;
    };

export type TrackPatternMap = Record<number, ArrangementPatternInput[]>;
export type TrackTemplateMap = Record<number, number>;

export type RawNoteRecord = {
  id: string;
  index: number;
  tick: number;
  gate: number;
  note: number;
  velocity: number;
  flags0: number;
  flags1: number;
};

export type PatternMetadata = {
  patternIndex: number;
  steps: number;
  scaleRaw: number;
  noteCount: number;
};

export type SongChain = {
  index: number;
  sceneChain: number[];
  loop: boolean;
  supported: boolean;
};

function hasBytesAt(
  source: Uint8Array,
  offset: number,
  expected: number[],
): boolean {
  if (offset < 0 || offset + expected.length > source.length) return false;
  return expected.every((value, index) => source[offset + index] === value);
}

function hasPlausiblePatternHeader(
  image: Uint8Array,
  start: number,
  leaderOnly: boolean,
): boolean {
  if (start < 0 || start + OFF_NOTE_COUNT >= image.length) return false;
  const countOrClone = image[start];
  if (leaderOnly ? countOrClone < 1 || countOrClone > 16 : countOrClone > 16) {
    return false;
  }
  const steps = image[start + OFF_PATTERN_STEPS];
  if (steps < 1 || steps > 64) return false;
  if (!hasBytesAt(image, start + 7, TRACK_HEADER_MAGIC)) return false;
  return image[start + OFF_NOTE_COUNT] <= 120;
}

function scanPatternHeaders(image: Uint8Array, leaderOnly: boolean): number[] {
  const starts: number[] = [];
  const limit = image.length - OFF_NOTE_COUNT;
  for (let start = 0; start < limit; start += 1) {
    if (hasPlausiblePatternHeader(image, start, leaderOnly)) {
      starts.push(start);
    }
  }
  return starts;
}

function u32ToBytes(value: number): Uint8Array {
  const buf = new Uint8Array(4);
  const view = new DataView(buf.buffer);
  view.setUint32(0, value, true); // little-endian
  return buf;
}

function u16ToBytes(value: number): Uint8Array {
  const buf = new Uint8Array(2);
  const view = new DataView(buf.buffer);
  view.setUint16(0, value, true); // little-endian
  return buf;
}

function concatBytes(parts: Uint8Array[]): Uint8Array {
  const total = parts.reduce((sum, part) => sum + part.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const part of parts) {
    out.set(part, offset);
    offset += part.length;
  }
  return out;
}

function replaceRangeBytes(
  source: Uint8Array,
  start: number,
  end: number,
  replacement: Uint8Array,
): Uint8Array {
  const out = new Uint8Array(
    source.length - (end - start) + replacement.length,
  );
  out.set(source.subarray(0, start), 0);
  out.set(replacement, start);
  out.set(source.subarray(end), start + replacement.length);
  return out;
}

function patternPayload(pattern: ArrangementPatternInput): {
  notes: PatternNoteInput[];
  steps?: number;
} {
  if (Array.isArray(pattern)) {
    return { notes: pattern };
  }
  let steps = pattern.steps;
  if (steps === undefined && pattern.bars !== undefined) {
    steps = pattern.bars * 16;
  }
  return { notes: pattern.notes ?? [], steps };
}

function patternStruct(
  baseStruct: Uint8Array,
  pattern: ArrangementPatternInput,
): Uint8Array {
  const { notes, steps } = patternPayload(pattern);
  const st = new Uint8Array(baseStruct);

  if (steps !== undefined) {
    if (steps < 1 || steps > 64) {
      throw new Error("pattern length must be 1..64 steps");
    }
    st[OFF_PATTERN_STEPS] = steps & 0xff;
    st[OFF_PRISTINE] = 0;
    st[OFF_PRISTINE + 1] = 0;
  }

  if (notes.length === 0) {
    return st;
  }

  if (notes.length > 120) {
    throw new Error("pattern note limit exceeded");
  }

  const maxStep = Math.max(...notes.map((note) => note.step));
  const inferredSteps = Math.min(
    64,
    Math.max(16, Math.ceil(maxStep / 16) * 16),
  );
  st[OFF_PATTERN_STEPS] = steps ?? inferredSteps;
  st[OFF_PRISTINE] = 0;
  st[OFF_PRISTINE + 1] = 0;

  const records = new Uint8Array(notes.length * NOTE_SIZE);
  const recordView = new DataView(records.buffer);
  notes.forEach((input, index) => {
    const tickOffset = input.tickOffset ?? input.tick_offset ?? 0;
    const gate = input.gateTicks ?? input.gate_ticks ?? 240;
    const tick = (input.step - 1) * STEP_TICKS + tickOffset;
    const offset = index * NOTE_SIZE;
    recordView.setUint32(offset, Math.max(0, Math.round(tick)), true);
    recordView.setUint32(offset + 4, Math.max(1, Math.round(gate)), true);
    records[offset + 8] =
      Math.max(0, Math.min(127, Math.round(input.note))) & 0x7f;
    records[offset + 9] =
      Math.max(0, Math.min(127, Math.round(input.velocity ?? 100))) & 0x7f;
    records[offset + 10] = 0;
    records[offset + 11] = 0;
  });

  st[OFF_NOTE_COUNT] = notes.length;
  return replaceRangeBytes(st, OFF_NOTE_COUNT + 1, OFF_NOTE_COUNT + 1, records);
}

export function leaderStartsFromImage(image: Uint8Array): number[] {
  const scanned = scanPatternHeaders(image, true);
  if (scanned.length === TRACK_COUNT) {
    return scanned;
  }

  const leaders: number[] = [];
  let pos = TRACK_BASE0;
  for (let i = 0; i < TRACK_COUNT; i++) {
    if (pos < 0 || pos + TRACK_STRIDE > image.length) {
      return [];
    }
    leaders.push(pos);
    let patternCount = image[pos];
    if (patternCount < 1 || patternCount > 16) {
      patternCount = 1;
    }
    if (pos + OFF_NOTE_COUNT >= image.length) {
      return [];
    }
    let noteCount = image[pos + OFF_NOTE_COUNT];
    if (noteCount > 120) {
      return [];
    }
    pos += TRACK_STRIDE + noteCount * NOTE_SIZE;
    for (let pattern = 1; pattern < patternCount; pattern++) {
      const cloneStart = pos - 1;
      if (cloneStart + OFF_NOTE_COUNT >= image.length) {
        return [];
      }
      noteCount = image[cloneStart + OFF_NOTE_COUNT];
      if (noteCount > 120) {
        return [];
      }
      pos = cloneStart + TRACK_STRIDE + noteCount * NOTE_SIZE;
    }
  }
  return leaders;
}

export function patternStartsFromImage(image: Uint8Array): number[][] {
  const leaders = leaderStartsFromImage(image);
  if (leaders.length === TRACK_COUNT) {
    const physicalStarts = scanPatternHeaders(image, false);
    return leaders.map((leader, index) => {
      const nextLeader = leaders[index + 1] ?? image.length;
      const starts = physicalStarts.filter(
        (start) => start >= leader && start < nextLeader,
      );
      return starts.length > 0 ? starts : [leader];
    });
  }

  const trackPatterns: number[][] = [];
  let pos = TRACK_BASE0;
  for (let i = 0; i < TRACK_COUNT; i++) {
    const patternStarts: number[] = [];
    if (pos < 0 || pos + TRACK_STRIDE > image.length) {
      return trackPatterns;
    }
    let patternCount = image[pos];
    if (patternCount < 1 || patternCount > 16) {
      patternCount = 1;
    }
    patternStarts.push(pos);
    if (pos + OFF_NOTE_COUNT >= image.length) {
      return trackPatterns;
    }
    let noteCount = image[pos + OFF_NOTE_COUNT];
    if (noteCount > 120) {
      return trackPatterns;
    }
    pos += TRACK_STRIDE + noteCount * NOTE_SIZE;
    for (let pattern = 1; pattern < patternCount; pattern++) {
      const cloneStart = pos - 1;
      if (cloneStart + OFF_NOTE_COUNT >= image.length) {
        return trackPatterns;
      }
      patternStarts.push(cloneStart);
      noteCount = image[cloneStart + OFF_NOTE_COUNT];
      if (noteCount > 120) {
        return trackPatterns;
      }
      pos = cloneStart + TRACK_STRIDE + noteCount * NOTE_SIZE;
    }
    trackPatterns.push(patternStarts);
  }
  return trackPatterns;
}

export function trackDataEndFromImage(image: Uint8Array): number | null {
  let pos = TRACK_BASE0;
  for (let i = 0; i < TRACK_COUNT; i++) {
    if (pos < 0 || pos + TRACK_STRIDE > image.length) {
      return null;
    }
    let patternCount = image[pos];
    if (patternCount < 1 || patternCount > 16) {
      patternCount = 1;
    }
    if (pos + OFF_NOTE_COUNT >= image.length) {
      return null;
    }
    let noteCount = image[pos + OFF_NOTE_COUNT];
    if (noteCount > 120) {
      return null;
    }
    pos += TRACK_STRIDE + noteCount * NOTE_SIZE;
    for (let pattern = 1; pattern < patternCount; pattern++) {
      const cloneStart = pos - 1;
      if (cloneStart + OFF_NOTE_COUNT >= image.length) {
        return null;
      }
      noteCount = image[cloneStart + OFF_NOTE_COUNT];
      if (noteCount > 120) {
        return null;
      }
      pos = cloneStart + TRACK_STRIDE + noteCount * NOTE_SIZE;
    }
  }
  return pos;
}

export function buildArrangementFromBytes(
  baselineBytes: Uint8Array,
  trackPatterns: TrackPatternMap,
  trackTemplates: TrackTemplateMap = {},
): Uint8Array {
  const { header, image: base } = decodeProject(baselineBytes);
  const starts = leaderStartsFromImage(base);
  if (starts.length !== TRACK_COUNT) {
    throw new Error("could not locate baseline track structs");
  }

  const parts: Uint8Array[] = [base.slice(0, starts[0])];

  for (let track = 1; track <= TRACK_COUNT; track++) {
    const start = starts[track - 1];
    const templateTrack = trackTemplates[track] ?? track;
    if (templateTrack < 1 || templateTrack > TRACK_COUNT) {
      throw new Error(`invalid template track ${templateTrack} for T${track}`);
    }
    const templateStart = starts[templateTrack - 1];
    const baseStruct = base.subarray(
      templateStart,
      templateStart + TRACK_STRIDE,
    );
    const tail =
      track === TRACK_COUNT
        ? base.subarray(start + TRACK_STRIDE)
        : new Uint8Array();
    const patterns = trackPatterns[track];

    if (!patterns || patterns.length === 0) {
      parts.push(concatBytes([baseStruct, tail]));
      continue;
    }

    if (patterns.length > 16) {
      throw new Error("OP-XY tracks support at most 16 patterns");
    }

    const structs = patterns.map((pattern) =>
      patternStruct(baseStruct, pattern),
    );
    const leader = new Uint8Array(structs[0]);
    leader[0] = patterns.length;
    const clones = structs.slice(1).map((st) => st.subarray(1));
    parts.push(concatBytes([leader, ...clones, tail]));
  }

  return encodeProject(header, concatBytes(parts));
}

// Basic implementation of the ImageProject functionality
export class ImageProject {
  public header: Uint8Array;
  public image: Uint8Array;
  private starts: number[] = [];
  private patternStarts: number[][] = [];
  private sceneSlot0 = SCENE_SLOT0;

  constructor(header: Uint8Array, image: Uint8Array) {
    this.header = header;
    this.image = image;
    this.rescan();
  }

  static fromBytes(data: Uint8Array): ImageProject {
    const { header, image } = decodeProject(data);
    return new ImageProject(header, image);
  }

  private rescan(): void {
    const starts = leaderStartsFromImage(this.image);
    if (starts.length > 0) {
      this.starts = starts;
      this.sceneSlot0 = Math.max(0, starts[0] - TRACK_TO_SCENE_SLOT_DELTA);
    } else {
      this.starts = [];
      this.sceneSlot0 = SCENE_SLOT0;
    }

    const pStarts = patternStartsFromImage(this.image);
    if (pStarts.length > 0) {
      this.patternStarts = pStarts;
    } else {
      this.patternStarts = [];
    }
  }

  public trackStart(track: number): number {
    return this.starts[track - 1];
  }

  public trackPatternStart(track: number, patternIndex: number): number {
    const patternsForTrack = this.patternStarts[track - 1];
    if (!patternsForTrack || patternIndex >= patternsForTrack.length) {
      throw new Error(`Pattern ${patternIndex} not found on track ${track}`);
    }
    return patternsForTrack[patternIndex];
  }

  public getPatternCount(track: number): number {
    const patternsForTrack = this.patternStarts[track - 1];
    return patternsForTrack ? patternsForTrack.length : 0;
  }

  public markEdited(track: number): void {
    const s = this.trackStart(track);
    this.image.set([0x00, 0x00], s + OFF_PRISTINE);
  }

  public markPatternEdited(track: number, patternIndex: number = 0): void {
    const s = this.trackPatternStart(track, patternIndex);
    this.image.set([0x00, 0x00], s + OFF_PRISTINE);
  }

  public getTempo(): number {
    const view = new DataView(this.image.buffer);
    return view.getUint16(GLOBAL_TEMPO, true) / 10.0;
  }

  public setTempo(bpm: number): void {
    const view = new DataView(this.image.buffer);
    view.setUint16(GLOBAL_TEMPO, Math.round(bpm * 10), true);
  }

  public getPatternSteps(track: number, patternIndex: number = 0): number {
    const s = this.trackPatternStart(track, patternIndex);
    return this.image[s + OFF_PATTERN_STEPS];
  }

  public setPatternSteps(
    track: number,
    steps: number,
    patternIndex: number = 0,
  ): void {
    if (steps < 1 || steps > 64) {
      throw new Error("pattern length must be 1..64 steps");
    }
    const s = this.trackPatternStart(track, patternIndex);
    this.image[s + OFF_PATTERN_STEPS] = steps & 0xff;
    this.markPatternEdited(track, patternIndex);
  }

  public getTrackScaleRaw(track: number, patternIndex: number = 0): number {
    const s = this.trackPatternStart(track, patternIndex);
    return this.image[s + OFF_SCALE];
  }

  public setTrackScaleRaw(
    track: number,
    raw: number,
    patternIndex: number = 0,
  ): void {
    if (raw < 0 || raw > 0xff) {
      throw new Error("track scale raw value must be 0..255");
    }
    const s = this.trackPatternStart(track, patternIndex);
    this.image[s + OFF_SCALE] = raw & 0xff;
    this.markPatternEdited(track, patternIndex);
  }

  public getPatternMetadata(
    track: number,
    patternIndex: number = 0,
  ): PatternMetadata {
    return {
      patternIndex,
      steps: this.getPatternSteps(track, patternIndex),
      scaleRaw: this.getTrackScaleRaw(track, patternIndex),
      noteCount: this.noteCount(track, patternIndex),
    };
  }

  public noteCount(track: number, patternIndex: number = 0): number {
    return this.image[
      this.trackPatternStart(track, patternIndex) + OFF_NOTE_COUNT
    ];
  }

  public addNote(
    track: number,
    {
      step,
      tick,
      note,
      velocity = 100,
      gate = 240,
      flags0 = 0,
      flags1 = 0,
      patternIndex = 0,
    }: {
      step?: number;
      tick?: number;
      note: number;
      velocity?: number;
      gate?: number;
      flags0?: number;
      flags1?: number;
      patternIndex?: number;
    },
  ): void {
    if (tick === undefined) {
      if (step === undefined) {
        throw new Error("need step or tick");
      }
      tick = (step - 1) * STEP_TICKS;
    }

    const s = this.trackPatternStart(track, patternIndex);
    const cpos = s + OFF_NOTE_COUNT;
    const count = this.image[cpos];
    if (count >= 120) {
      throw new Error("pattern note limit reached");
    }

    const tickBytes = u32ToBytes(tick);
    const gateBytes = u32ToBytes(gate);
    const rec = new Uint8Array([
      ...tickBytes,
      ...gateBytes,
      note & 0x7f,
      velocity & 0x7f,
      flags0 & 0xff,
      flags1 & 0xff,
    ]);

    const insertAt = cpos + 1 + count * NOTE_SIZE;

    // Splice array
    const newImage = new Uint8Array(this.image.length + rec.length);
    newImage.set(this.image.subarray(0, insertAt), 0);
    newImage.set(rec, insertAt);
    newImage.set(this.image.subarray(insertAt), insertAt + rec.length);

    this.image = newImage;
    this.image[cpos] = count + 1;

    this.markEdited(track);
    this.rescan();
  }

  private noteOffset(
    track: number,
    patternIndex: number,
    noteIndex: number,
  ): number {
    const s = this.trackPatternStart(track, patternIndex);
    const cpos = s + OFF_NOTE_COUNT;
    const count = this.image[cpos];
    if (noteIndex < 0 || noteIndex >= count) {
      throw new Error(
        `note ${noteIndex} not found on track ${track} pattern ${patternIndex}`,
      );
    }
    return cpos + 1 + noteIndex * NOTE_SIZE;
  }

  public getNotes(track: number, patternIndex: number = 0): RawNoteRecord[] {
    const s = this.trackPatternStart(track, patternIndex);
    const cpos = s + OFF_NOTE_COUNT;
    const count = this.image[cpos];
    const notes: RawNoteRecord[] = [];

    const view = new DataView(this.image.buffer);

    for (let i = 0; i < count; i++) {
      const offset = cpos + 1 + i * NOTE_SIZE;
      const tick = view.getUint32(offset, true);
      const gate = view.getUint32(offset + 4, true);
      const note = this.image[offset + 8];
      const velocity = this.image[offset + 9];
      const flags0 = this.image[offset + 10];
      const flags1 = this.image[offset + 11];
      notes.push({
        id: `t${track - 1}:p${patternIndex}:n${i}`,
        index: i,
        tick,
        gate,
        note,
        velocity,
        flags0,
        flags1,
      });
    }

    return notes;
  }

  public updateNote(
    track: number,
    patternIndex: number,
    noteIndex: number,
    patch: Partial<Pick<RawNoteRecord, "tick" | "gate" | "note" | "velocity">>,
  ): void {
    const offset = this.noteOffset(track, patternIndex, noteIndex);
    const view = new DataView(this.image.buffer);
    if (patch.tick !== undefined) {
      view.setUint32(offset, Math.max(0, Math.round(patch.tick)), true);
    }
    if (patch.gate !== undefined) {
      view.setUint32(offset + 4, Math.max(1, Math.round(patch.gate)), true);
    }
    if (patch.note !== undefined) {
      this.image[offset + 8] =
        Math.max(0, Math.min(127, Math.round(patch.note))) & 0x7f;
    }
    if (patch.velocity !== undefined) {
      this.image[offset + 9] =
        Math.max(0, Math.min(127, Math.round(patch.velocity))) & 0x7f;
    }
    this.markPatternEdited(track, patternIndex);
  }

  public deleteNote(
    track: number,
    patternIndex: number,
    noteIndex: number,
  ): void {
    const s = this.trackPatternStart(track, patternIndex);
    const cpos = s + OFF_NOTE_COUNT;
    const count = this.image[cpos];
    if (noteIndex < 0 || noteIndex >= count) {
      throw new Error(
        `note ${noteIndex} not found on track ${track} pattern ${patternIndex}`,
      );
    }

    const removeAt = cpos + 1 + noteIndex * NOTE_SIZE;
    const newImage = new Uint8Array(this.image.length - NOTE_SIZE);
    newImage.set(this.image.subarray(0, removeAt), 0);
    newImage.set(this.image.subarray(removeAt + NOTE_SIZE), removeAt);
    this.image = newImage;
    this.image[cpos] = count - 1;
    this.markPatternEdited(track, patternIndex);
    this.rescan();
  }

  // --- scenes (arrangement) ---
  public getScenePattern(sceneIndex: number, trackIndex: number): number {
    const slot = this.sceneSlot0 + sceneIndex * SCENE_SLOT_SIZE;
    return this.image[slot + trackIndex - 1]; // Tracks are 1-indexed for the API but 0-indexed in array here
  }

  public setScenePattern(
    sceneIndex: number,
    trackIndex: number,
    patternIndex: number,
  ): void {
    const slot = this.sceneSlot0 + sceneIndex * SCENE_SLOT_SIZE;
    this.image[slot + trackIndex - 1] = patternIndex;
    this.image[slot + 32] = 1; // flag
  }

  public getSceneMute(sceneIndex: number, trackIndex: number): boolean {
    const slot = this.sceneSlot0 + sceneIndex * SCENE_SLOT_SIZE;
    return this.image[slot + 16 + trackIndex - 1] !== 0;
  }

  public setSceneMute(
    sceneIndex: number,
    trackIndex: number,
    muted: boolean,
  ): void {
    const slot = this.sceneSlot0 + sceneIndex * SCENE_SLOT_SIZE;
    this.image[slot + 16 + trackIndex - 1] = muted ? SCENE_MUTE_VALUE : 0;
    this.image[slot + 32] = 1;
  }

  public getScenePresent(sceneIndex: number): boolean {
    const slot = this.sceneSlot0 + sceneIndex * SCENE_SLOT_SIZE;
    return this.image[slot + 32] !== 0;
  }

  public setScenePresent(sceneIndex: number, present: boolean): void {
    const slot = this.sceneSlot0 + sceneIndex * SCENE_SLOT_SIZE;
    this.image[slot + 32] = present ? 1 : 0;
  }

  public getSceneRow(sceneIndex: number): {
    patterns: number[];
    mutes: boolean[];
    present: boolean;
  } {
    return {
      patterns: Array.from({ length: TRACK_COUNT }, (_, i) =>
        this.getScenePattern(sceneIndex, i + 1),
      ),
      mutes: Array.from({ length: TRACK_COUNT }, (_, i) =>
        this.getSceneMute(sceneIndex, i + 1),
      ),
      present: this.getScenePresent(sceneIndex),
    };
  }

  public setSceneRow(
    sceneIndex: number,
    patterns: number[],
    mutes: boolean[],
  ): void {
    const slot = this.sceneSlot0 + sceneIndex * SCENE_SLOT_SIZE;
    for (let i = 0; i < TRACK_COUNT; i++) {
      this.image[slot + i] = Math.max(0, Math.min(8, patterns[i] ?? 0));
      this.image[slot + 16 + i] = mutes[i] ? SCENE_MUTE_VALUE : 0;
    }
    this.image[slot + 32] = 1;
  }

  public duplicateScene(
    sourceSceneIndex: number,
    targetSceneIndex: number,
  ): void {
    const source = this.sceneSlot0 + sourceSceneIndex * SCENE_SLOT_SIZE;
    const target = this.sceneSlot0 + targetSceneIndex * SCENE_SLOT_SIZE;
    this.image.set(
      this.image.subarray(source, source + SCENE_SLOT_SIZE),
      target,
    );
    this.image[target + 32] = 1;
  }

  public resetScene(sceneIndex: number): void {
    this.setSceneRow(
      sceneIndex,
      Array(TRACK_COUNT).fill(0),
      Array(TRACK_COUNT).fill(false),
    );
  }

  private footerStart(): number {
    const end = trackDataEndFromImage(this.image);
    if (end !== null && end >= 0 && end < this.image.length) {
      return end;
    }
    return Math.max(
      0,
      this.image.length - SONG_FOOTER_SLOTS * SONG_DEFAULT_SLOT_SIZE,
    );
  }

  private songSlotLengthAt(offset: number): number {
    const count = this.image[offset];
    if (count > SONG_MAX_CHAIN || offset + 1 + count + 2 > this.image.length) {
      return SONG_DEFAULT_SLOT_SIZE;
    }
    return 1 + count + 2;
  }

  public getSongChain(songIndex: number = 0): SongChain {
    if (songIndex !== 0) {
      return {
        index: songIndex,
        sceneChain: [],
        loop: false,
        supported: false,
      };
    }
    const start = this.footerStart();
    const count = this.image[start];
    if (count > SONG_MAX_CHAIN || start + 1 + count + 2 > this.image.length) {
      return {
        index: songIndex,
        sceneChain: [],
        loop: false,
        supported: false,
      };
    }
    const sceneChain = Array.from(
      this.image.subarray(start + 1, start + 1 + count),
    );
    const loopA = this.image[start + 1 + count];
    const loopB = this.image[start + 1 + count + 1];
    return {
      index: songIndex,
      sceneChain,
      loop: loopA === 0 && loopB === 1,
      supported: true,
    };
  }

  public setSongChain(
    songIndex: number,
    sceneChain: number[],
    loop: boolean = true,
  ): void {
    if (songIndex !== 0) {
      throw new Error("only Song 1 write support is enabled in the web app");
    }
    if (sceneChain.length > SONG_MAX_CHAIN) {
      throw new Error(`song chain cannot exceed ${SONG_MAX_CHAIN} scenes`);
    }
    for (const scene of sceneChain) {
      if (scene < 0 || scene >= SCENE_COUNT) {
        throw new Error("song scene references must be 0..98");
      }
    }

    const start = this.footerStart();
    const oldLength = this.songSlotLengthAt(start);
    const slot = new Uint8Array(1 + sceneChain.length + 2);
    slot[0] = sceneChain.length;
    slot.set(sceneChain, 1);
    slot[1 + sceneChain.length] = loop ? 0 : 1;
    slot[1 + sceneChain.length + 1] = loop ? 1 : 0;

    const newImage = new Uint8Array(
      this.image.length - oldLength + slot.length,
    );
    newImage.set(this.image.subarray(0, start), 0);
    newImage.set(slot, start);
    newImage.set(this.image.subarray(start + oldLength), start + slot.length);
    this.image = newImage;
    this.rescan();
  }

  public toBytes(): Uint8Array {
    return encodeProject(this.header, this.image);
  }
}
