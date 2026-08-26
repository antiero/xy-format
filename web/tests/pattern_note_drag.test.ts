import { describe, expect, it } from "vitest";
import { pointerDeltaTo16ths } from "../src/lib/xy/patternNoteDrag";

describe("pattern note pointer drag", () => {
  it("updates within a single sixteenth-note cell", () => {
    expect(pointerDeltaTo16ths(8.5, 34)).toBe(0.25);
    expect(pointerDeltaTo16ths(-8.5, 34)).toBe(-0.25);
  });

  it("retains whole-cell movement and guards invalid zoom", () => {
    expect(pointerDeltaTo16ths(68, 34)).toBe(2);
    expect(pointerDeltaTo16ths(20, 0)).toBe(0);
  });
});
