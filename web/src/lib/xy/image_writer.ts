import { decodeProject, encodeProject } from './rle';

export const TRACK_BASE0 = 0x0D79;
export const TRACK_STRIDE = 17876;
export const TRACK_COUNT = 16;

export const OFF_PATTERN_STEPS = 0x01;
export const OFF_BARS = OFF_PATTERN_STEPS;
export const OFF_SCALE = 0x06;
export const OFF_QUANTIZATION = 0x07;
export const OFF_TRACK_GROOVE = 0x08;
export const OFF_PRISTINE = 0x11;
export const OFF_PLOCK_SHAPE = 0x3056;
export const OFF_NOTE_COUNT = 0x456F;
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

export function leaderStartsFromImage(image: Uint8Array): number[] {
  const leaders: number[] = [];
  let pos = TRACK_BASE0;
  for (let i = 0; i < TRACK_COUNT; i++) {
    if (pos < 0 || pos + TRACK_STRIDE > image.length) {
      return [];
    }
    leaders.push(pos);
    let patternCount = image[pos];
    if (patternCount < 1 || patternCount > 9) {
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
  const trackPatterns: number[][] = [];
  let pos = TRACK_BASE0;
  for (let i = 0; i < TRACK_COUNT; i++) {
    const patternStarts: number[] = [];
    if (pos < 0 || pos + TRACK_STRIDE > image.length) {
      return trackPatterns;
    }
    let patternCount = image[pos];
    if (patternCount < 1 || patternCount > 9) {
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
    if (patternCount < 1 || patternCount > 9) {
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

// Basic implementation of the ImageProject functionality
export class ImageProject {
  public header: Uint8Array;
  public image: Uint8Array;
  private starts: number[] = [];
  private patternStarts: number[][] = [];

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
    } else {
        this.starts = [];
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

  public setPatternSteps(track: number, steps: number, patternIndex: number = 0): void {
    if (steps < 1 || steps > 64) {
      throw new Error('pattern length must be 1..64 steps');
    }
    const s = this.trackPatternStart(track, patternIndex);
    this.image[s + OFF_PATTERN_STEPS] = steps & 0xFF;
    this.markPatternEdited(track, patternIndex);
  }

  public getTrackScaleRaw(track: number, patternIndex: number = 0): number {
    const s = this.trackPatternStart(track, patternIndex);
    return this.image[s + OFF_SCALE];
  }

  public setTrackScaleRaw(track: number, raw: number, patternIndex: number = 0): void {
    if (raw < 0 || raw > 0xFF) {
      throw new Error('track scale raw value must be 0..255');
    }
    const s = this.trackPatternStart(track, patternIndex);
    this.image[s + OFF_SCALE] = raw & 0xFF;
    this.markPatternEdited(track, patternIndex);
  }

  public getPatternMetadata(track: number, patternIndex: number = 0): PatternMetadata {
    return {
      patternIndex,
      steps: this.getPatternSteps(track, patternIndex),
      scaleRaw: this.getTrackScaleRaw(track, patternIndex),
      noteCount: this.noteCount(track, patternIndex),
    };
  }

  public noteCount(track: number, patternIndex: number = 0): number {
    return this.image[this.trackPatternStart(track, patternIndex) + OFF_NOTE_COUNT];
  }

  public addNote(
    track: number,
    { step, tick, note, velocity = 100, gate = 240, patternIndex = 0 }: { step?: number; tick?: number; note: number; velocity?: number; gate?: number; patternIndex?: number }
  ): void {
    if (tick === undefined) {
      if (step === undefined) {
        throw new Error('need step or tick');
      }
      tick = (step - 1) * STEP_TICKS;
    }

    const s = this.trackPatternStart(track, patternIndex);
    const cpos = s + OFF_NOTE_COUNT;
    const count = this.image[cpos];
    if (count >= 120) {
      throw new Error('pattern note limit reached');
    }

    const tickBytes = u32ToBytes(tick);
    const gateBytes = u32ToBytes(gate);
    const rec = new Uint8Array([...tickBytes, ...gateBytes, note & 0x7F, velocity & 0x7F, 0, 0]);

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

  private noteOffset(track: number, patternIndex: number, noteIndex: number): number {
    const s = this.trackPatternStart(track, patternIndex);
    const cpos = s + OFF_NOTE_COUNT;
    const count = this.image[cpos];
    if (noteIndex < 0 || noteIndex >= count) {
      throw new Error(`note ${noteIndex} not found on track ${track} pattern ${patternIndex}`);
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
          id: `t${track - 1}:p${patternIndex}:n${i}:x${tick}:m${note}`,
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
    patch: Partial<Pick<RawNoteRecord, 'tick' | 'gate' | 'note' | 'velocity'>>
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
      this.image[offset + 8] = Math.max(0, Math.min(127, Math.round(patch.note))) & 0x7F;
    }
    if (patch.velocity !== undefined) {
      this.image[offset + 9] = Math.max(0, Math.min(127, Math.round(patch.velocity))) & 0x7F;
    }
    this.markPatternEdited(track, patternIndex);
  }

  public deleteNote(track: number, patternIndex: number, noteIndex: number): void {
    const s = this.trackPatternStart(track, patternIndex);
    const cpos = s + OFF_NOTE_COUNT;
    const count = this.image[cpos];
    if (noteIndex < 0 || noteIndex >= count) {
      throw new Error(`note ${noteIndex} not found on track ${track} pattern ${patternIndex}`);
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
    const slot = SCENE_SLOT0 + sceneIndex * SCENE_SLOT_SIZE;
    return this.image[slot + trackIndex - 1]; // Tracks are 1-indexed for the API but 0-indexed in array here
  }

  public setScenePattern(sceneIndex: number, trackIndex: number, patternIndex: number): void {
      const slot = SCENE_SLOT0 + sceneIndex * SCENE_SLOT_SIZE;
      this.image[slot + trackIndex - 1] = patternIndex;
      this.image[slot + 32] = 1; // flag
  }

  public getSceneMute(sceneIndex: number, trackIndex: number): boolean {
    const slot = SCENE_SLOT0 + sceneIndex * SCENE_SLOT_SIZE;
    return this.image[slot + 16 + trackIndex - 1] !== 0;
  }

  public setSceneMute(sceneIndex: number, trackIndex: number, muted: boolean): void {
    const slot = SCENE_SLOT0 + sceneIndex * SCENE_SLOT_SIZE;
    this.image[slot + 16 + trackIndex - 1] = muted ? SCENE_MUTE_VALUE : 0;
    this.image[slot + 32] = 1;
  }

  public getScenePresent(sceneIndex: number): boolean {
    const slot = SCENE_SLOT0 + sceneIndex * SCENE_SLOT_SIZE;
    return this.image[slot + 32] !== 0;
  }

  public setScenePresent(sceneIndex: number, present: boolean): void {
    const slot = SCENE_SLOT0 + sceneIndex * SCENE_SLOT_SIZE;
    this.image[slot + 32] = present ? 1 : 0;
  }

  public getSceneRow(sceneIndex: number): { patterns: number[]; mutes: boolean[]; present: boolean } {
    return {
      patterns: Array.from({ length: TRACK_COUNT }, (_, i) => this.getScenePattern(sceneIndex, i + 1)),
      mutes: Array.from({ length: TRACK_COUNT }, (_, i) => this.getSceneMute(sceneIndex, i + 1)),
      present: this.getScenePresent(sceneIndex),
    };
  }

  public setSceneRow(sceneIndex: number, patterns: number[], mutes: boolean[]): void {
    const slot = SCENE_SLOT0 + sceneIndex * SCENE_SLOT_SIZE;
    for (let i = 0; i < TRACK_COUNT; i++) {
      this.image[slot + i] = Math.max(0, Math.min(8, patterns[i] ?? 0));
      this.image[slot + 16 + i] = mutes[i] ? SCENE_MUTE_VALUE : 0;
    }
    this.image[slot + 32] = 1;
  }

  public duplicateScene(sourceSceneIndex: number, targetSceneIndex: number): void {
    const source = SCENE_SLOT0 + sourceSceneIndex * SCENE_SLOT_SIZE;
    const target = SCENE_SLOT0 + targetSceneIndex * SCENE_SLOT_SIZE;
    this.image.set(this.image.subarray(source, source + SCENE_SLOT_SIZE), target);
    this.image[target + 32] = 1;
  }

  public resetScene(sceneIndex: number): void {
    this.setSceneRow(sceneIndex, Array(TRACK_COUNT).fill(0), Array(TRACK_COUNT).fill(false));
  }

  private footerStart(): number {
    const end = trackDataEndFromImage(this.image);
    if (end !== null && end >= 0 && end < this.image.length) {
      return end;
    }
    return Math.max(0, this.image.length - SONG_FOOTER_SLOTS * SONG_DEFAULT_SLOT_SIZE);
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
      return { index: songIndex, sceneChain: [], loop: false, supported: false };
    }
    const start = this.footerStart();
    const count = this.image[start];
    if (count > SONG_MAX_CHAIN || start + 1 + count + 2 > this.image.length) {
      return { index: songIndex, sceneChain: [], loop: false, supported: false };
    }
    const sceneChain = Array.from(this.image.subarray(start + 1, start + 1 + count));
    const loopA = this.image[start + 1 + count];
    const loopB = this.image[start + 1 + count + 1];
    return {
      index: songIndex,
      sceneChain,
      loop: loopA === 0 && loopB === 1,
      supported: true,
    };
  }

  public setSongChain(songIndex: number, sceneChain: number[], loop: boolean = true): void {
    if (songIndex !== 0) {
      throw new Error('only Song 1 write support is enabled in the web app');
    }
    if (sceneChain.length > SONG_MAX_CHAIN) {
      throw new Error(`song chain cannot exceed ${SONG_MAX_CHAIN} scenes`);
    }
    for (const scene of sceneChain) {
      if (scene < 0 || scene >= SCENE_COUNT) {
        throw new Error('song scene references must be 0..98');
      }
    }

    const start = this.footerStart();
    const oldLength = this.songSlotLengthAt(start);
    const slot = new Uint8Array(1 + sceneChain.length + 2);
    slot[0] = sceneChain.length;
    slot.set(sceneChain, 1);
    slot[1 + sceneChain.length] = loop ? 0 : 1;
    slot[1 + sceneChain.length + 1] = loop ? 1 : 0;

    const newImage = new Uint8Array(this.image.length - oldLength + slot.length);
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
