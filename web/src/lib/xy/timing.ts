import type {
  XYPatternViewModel,
  XYSceneViewModel,
  XYTrackScale,
  XYTrackViewModel,
} from "./projectViewModel";
import { STEP_TICKS } from "./image_writer";

export type PatternTimingMode = "step" | "raw";
export const STEP_TIMING_TOLERANCE_TICKS = Math.round(STEP_TICKS * 0.15);

export type DecodedPatternSteps = {
  raw: number;
  bars: number;
  finalBarSteps: number;
  totalSteps: number;
  valid: boolean;
};

export type DecodedTrackScale = {
  raw: number;
  scale: XYTrackScale;
  label: string;
  known: boolean;
  supportedForWrite: boolean;
  factor16ths: number | null;
};

export const TRACK_SCALE_TO_16THS_PER_STEP: Record<
  Exclude<XYTrackScale, "unknown">,
  number
> = {
  "1/2": 0.5,
  "1": 1,
  "2": 2,
  "3": 3,
  "4": 4,
  "6": 6,
  "8": 8,
  "16": 16,
};

export const WRITABLE_TRACK_SCALE_BYTES: Record<
  Exclude<XYTrackScale, "unknown" | "3" | "4" | "6" | "8">,
  number
> = {
  "1/2": 0x01,
  "1": 0x03,
  "2": 0x05,
  "16": 0x0e,
};

const READ_SCALE_BYTES: Record<number, XYTrackScale> = {
  0x01: "1/2",
  0x03: "1",
  0x05: "2",
  0x07: "4",
  0x0b: "8",
  0x0e: "16",
};

export function decodePatternSteps(raw: number): DecodedPatternSteps {
  const totalSteps = raw;
  const valid = Number.isInteger(raw) && raw >= 1 && raw <= 64;
  const clamped = valid ? raw : Math.max(1, Math.min(64, raw || 16));
  return {
    raw,
    bars: Math.ceil(clamped / 16),
    finalBarSteps: clamped % 16 || 16,
    totalSteps: clamped,
    valid,
  };
}

export function decodeTrackScale(raw: number): DecodedTrackScale {
  const scale = READ_SCALE_BYTES[raw] ?? "unknown";
  const factor16ths =
    scale === "unknown" ? null : TRACK_SCALE_TO_16THS_PER_STEP[scale];
  return {
    raw,
    scale,
    label:
      scale === "unknown"
        ? `unknown 0x${raw.toString(16).padStart(2, "0")}`
        : scale,
    known: scale !== "unknown",
    supportedForWrite:
      scale !== "unknown" &&
      Object.prototype.hasOwnProperty.call(WRITABLE_TRACK_SCALE_BYTES, scale),
    factor16ths,
  };
}

export function scaleTo16thsPerStep(scale: XYTrackScale): number | null {
  return scale === "unknown" ? null : TRACK_SCALE_TO_16THS_PER_STEP[scale];
}

export function signedTick(rawTick: number): number {
  return rawTick > 0x7fffffff ? rawTick - 0x100000000 : rawTick;
}

export function normalizeTickToPattern(
  rawTick: number,
  totalSteps: number,
): number {
  const patternTicks = Math.max(1, totalSteps) * STEP_TICKS;
  const signed = signedTick(rawTick);
  return ((signed % patternTicks) + patternTicks) % patternTicks;
}

export function clampTickToPatternDisplay(
  rawTick: number,
  totalSteps: number,
): number {
  const patternTicks = Math.max(1, totalSteps) * STEP_TICKS;
  const signed = signedTick(rawTick);
  return Math.max(0, Math.min(patternTicks - 1, signed));
}

export function tickToDisplayStep(rawTick: number, totalSteps: number): number {
  const signed = signedTick(rawTick);
  const nearestStep = Math.round(signed / STEP_TICKS);
  return Math.max(0, Math.min(Math.max(1, totalSteps) - 1, nearestStep));
}

export function tickToDisplayTick(rawTick: number, totalSteps: number): number {
  return tickToDisplayStep(rawTick, totalSteps) * STEP_TICKS;
}

export function tickToPlaybackPosition(
  rawTick: number,
  totalSteps: number,
  timingMode: PatternTimingMode = "raw",
): number {
  return timingMode === "step"
    ? tickToDisplayTick(rawTick, totalSteps)
    : clampTickToPatternDisplay(rawTick, totalSteps);
}

export function patternTimingMode(
  notes: Array<Pick<XYPatternViewModel["notes"][number], "tick">>,
): PatternTimingMode {
  if (notes.length === 0) return "step";
  return notes.every((note) => {
    const signed = signedTick(note.tick);
    const nearestStepTick = Math.round(signed / STEP_TICKS) * STEP_TICKS;
    return Math.abs(signed - nearestStepTick) <= STEP_TIMING_TOLERANCE_TICKS;
  })
    ? "step"
    : "raw";
}

export function patternEffectiveLength16ths(
  pattern: XYPatternViewModel,
): number {
  const factor = scaleTo16thsPerStep(pattern.trackScale);
  return factor === null ? pattern.totalSteps : pattern.totalSteps * factor;
}

export function noteToDisplayPosition(
  note: Pick<XYPatternViewModel["notes"][number], "tick" | "gateTicks">,
  pattern: Pick<XYPatternViewModel, "trackScale"> &
    Partial<Pick<XYPatternViewModel, "totalSteps" | "timingMode">>,
): { start16ths: number; duration16ths: number } {
  const factor = scaleTo16thsPerStep(pattern.trackScale) ?? 1;
  const tick = pattern.totalSteps
    ? tickToPlaybackPosition(
        note.tick,
        pattern.totalSteps,
        pattern.timingMode ?? "raw",
      )
    : note.tick;
  return {
    start16ths: (tick / STEP_TICKS) * factor,
    duration16ths: Math.max(1 / 16, (note.gateTicks / STEP_TICKS) * factor),
  };
}

export function sceneLength16ths(
  scene: XYSceneViewModel,
  tracks: XYTrackViewModel[],
): number {
  return Math.max(
    0,
    ...scene.patternByTrack.map((patternIndex, trackIndex) => {
      const pattern = tracks[trackIndex]?.patterns[patternIndex];
      if (
        !pattern ||
        (pattern.notes.length === 0 &&
          pattern.plocks.length === 0 &&
          pattern.stepComponents.length === 0)
      ) {
        return 0;
      }
      return pattern.effectiveLength16ths;
    }),
  );
}

export function display16thsAsBars(value: number): string {
  if (!Number.isFinite(value)) return "unknown";
  const bars = value / 16;
  if (Number.isInteger(bars)) return `${bars} bar${bars === 1 ? "" : "s"}`;
  return `${value.toFixed(value < 10 ? 1 : 0)} 16ths`;
}
