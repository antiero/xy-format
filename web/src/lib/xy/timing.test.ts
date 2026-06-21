import { describe, expect, it } from "vitest";
import { STEP_TICKS } from "./image_writer";
import {
  clampTickToPatternDisplay,
  noteToDisplayPosition,
  patternTimingMode,
  decodeTrackScale,
  tickToDisplayTick,
  tickToDisplayStep,
  tickToPlaybackPosition,
} from "./timing";

describe("timing display positions", () => {
  it("decodes OP-XY track scale byte 0x07 as scale 4", () => {
    expect(decodeTrackScale(0x07)).toMatchObject({
      scale: "4",
      label: "4",
      factor16ths: 4,
    });
  });

  it("decodes OP-XY track scale byte 0x0b as scale 8", () => {
    expect(decodeTrackScale(0x0b)).toMatchObject({
      scale: "8",
      label: "8",
      factor16ths: 8,
    });
  });

  it("keeps near-start negative ticks on step 1 instead of wrapping", () => {
    const rawNegative42Ticks = 0xffffffff - 41;

    expect(clampTickToPatternDisplay(rawNegative42Ticks, 16)).toBe(0);
    expect(tickToDisplayStep(rawNegative42Ticks, 16)).toBe(0);
    expect(tickToPlaybackPosition(rawNegative42Ticks, 16)).toBe(0);
  });

  it("rounds micro-timed notes to their nearest display step", () => {
    expect(tickToDisplayStep(1970, 16)).toBe(4);
    expect(tickToDisplayStep(3403, 16)).toBe(7);
    expect(tickToDisplayStep(4797, 16)).toBe(10);
    expect(tickToDisplayStep(5753, 16)).toBe(12);

    expect(tickToDisplayTick(1970, 16)).toBe(STEP_TICKS * 4);
    expect(tickToPlaybackPosition(3403, 16, "step")).toBe(STEP_TICKS * 7);
  });

  it("uses zero-based display steps for exact grid ticks", () => {
    expect(tickToDisplayStep(0, 16)).toBe(0);
    expect(tickToDisplayStep(STEP_TICKS * 4, 16)).toBe(4);
    expect(tickToDisplayStep(STEP_TICKS * 12, 16)).toBe(12);
  });

  it("places imported step notes exactly on the displayed OP-XY grid", () => {
    const starts = [-42, 1970, 3403, 4797, 5753].map(
      (tick) =>
        noteToDisplayPosition(
          { tick: tick < 0 ? tick + 0x100000000 : tick, gateTicks: STEP_TICKS },
          { trackScale: "1", totalSteps: 16, timingMode: "step" },
        ).start16ths,
    );

    expect(starts).toEqual([0, 4, 7, 10, 12]);
  });

  it("preserves raw timing for deliberately off-grid patterns", () => {
    expect(patternTimingMode([{ tick: 0 }, { tick: 680 }])).toBe("raw");
    expect(tickToPlaybackPosition(680, 16, "raw")).toBe(680);

    const position = noteToDisplayPosition(
      { tick: 680, gateTicks: STEP_TICKS },
      { trackScale: "4", totalSteps: 16, timingMode: "raw" },
    );

    expect(position.start16ths).toBeCloseTo(5.6666667);
  });

  it("detects small OP-XY step nudges as step timing", () => {
    expect(
      patternTimingMode([
        { tick: 0xffffffff - 41 },
        { tick: 1970 },
        { tick: 3403 },
        { tick: 4797 },
        { tick: 5753 },
      ]),
    ).toBe("step");
  });
});
