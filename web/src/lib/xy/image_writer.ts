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

export const SCENE_SLOT0 = 0x95;
export const SCENE_SLOT_SIZE = 33;

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

  public setPatternSteps(track: number, steps: number): void {
    if (steps < 1 || steps > 64) {
      throw new Error('pattern length must be 1..64 steps');
    }
    const s = this.trackStart(track);
    this.image[s + OFF_PATTERN_STEPS] = steps & 0xFF;
    this.markEdited(track);
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

  public getNotes(track: number, patternIndex: number = 0): {tick: number, gate: number, note: number, velocity: number}[] {
    const s = this.trackPatternStart(track, patternIndex);
    const cpos = s + OFF_NOTE_COUNT;
    const count = this.image[cpos];
    const notes = [];

    const view = new DataView(this.image.buffer);

    for (let i = 0; i < count; i++) {
        const offset = cpos + 1 + i * NOTE_SIZE;
        const tick = view.getUint32(offset, true);
        const gate = view.getUint32(offset + 4, true);
        const note = this.image[offset + 8];
        const velocity = this.image[offset + 9];
        notes.push({tick, gate, note, velocity});
    }

    return notes;
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

  public toBytes(): Uint8Array {
    return encodeProject(this.header, this.image);
  }
}
