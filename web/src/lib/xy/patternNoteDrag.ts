import { STEP_TICKS } from "./image_writer";

/**
 * Convert horizontal pointer travel into the finest useful OP-XY piano-roll
 * increment. This keeps drag feedback live while still landing on exact
 * integer project ticks when the edit is committed.
 */
export function pointerDeltaTo16ths(
  deltaPixels: number,
  pixelsPer16th: number,
): number {
  if (!Number.isFinite(deltaPixels) || pixelsPer16th <= 0) return 0;
  const raw16ths = deltaPixels / pixelsPer16th;
  return Math.round(raw16ths * STEP_TICKS) / STEP_TICKS;
}
