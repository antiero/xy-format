import { describe, expect, it } from "vitest";
import { STEP_TICKS } from "./image_writer";
import { groupNotesByDisplayStep } from "./patternStepState";

const note = (id: string, step: number) => ({
  id,
  tick: step * STEP_TICKS,
});

describe("groupNotesByDisplayStep", () => {
  it("keeps step lights aligned across bar boundaries", () => {
    const grouped = groupNotesByDisplayStep(
      [note("bar-1", 15), note("bar-2", 16), note("bar-4", 63)],
      64,
    );

    expect(grouped.get(15)?.map(({ id }) => id)).toEqual(["bar-1"]);
    expect(grouped.get(16)?.map(({ id }) => id)).toEqual(["bar-2"]);
    expect(grouped.get(63)?.map(({ id }) => id)).toEqual(["bar-4"]);
  });

  it("lights one step for every note in a chord", () => {
    const grouped = groupNotesByDisplayStep(
      [note("root", 9), note("third", 9), note("fifth", 9)],
      16,
    );

    expect(grouped.get(9)?.map(({ id }) => id)).toEqual([
      "root",
      "third",
      "fifth",
    ]);
  });

  it("follows a piano-roll note while its tick is being edited", () => {
    const notes = [note("moving", 2), note("still", 18)];
    const grouped = groupNotesByDisplayStep(notes, 64, {
      moving: { tick: 32 * STEP_TICKS },
    });

    expect(grouped.has(2)).toBe(false);
    expect(grouped.get(18)?.map(({ id }) => id)).toEqual(["still"]);
    expect(grouped.get(32)?.map(({ id }) => id)).toEqual(["moving"]);
  });
});
