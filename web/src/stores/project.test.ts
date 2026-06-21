import { readFileSync } from "node:fs";
import { beforeEach, describe, expect, it } from "vitest";
import { get } from "svelte/store";
import { STEP_TICKS } from "../lib/xy/image_writer";
import { loadXYBytes } from "../lib/xy/projectLoader";
import {
  projectPatternDataCount,
  projectSummary,
  projectTracksWithStepData,
} from "../lib/xy/projectViewModel";
import {
  dispatchProjectEdit,
  editHistoryStore,
  projectStore,
  redoProjectEdit,
  undoProjectEdit,
} from "./project";

function loadBlankProject() {
  const bytes = readFileSync(
    new URL("../../public/baselines/blank.xy", import.meta.url),
  );
  return loadXYBytes(new Uint8Array(bytes), "blank.xy");
}

function activeNotes() {
  const project = get(projectStore);
  if (!project) throw new Error("project not loaded");
  return project.tracks[0].patterns[0].notes;
}

describe("project edit history", () => {
  beforeEach(() => {
    projectStore.set(loadBlankProject());
  });

  it("applies batch note edits with stable note ids", () => {
    expect(projectTracksWithStepData(get(projectStore)!)).toHaveLength(0);
    expect(projectPatternDataCount(get(projectStore)!)).toBe(0);
    expect(projectSummary(get(projectStore)!)).toContain("0 tracks");

    dispatchProjectEdit({
      type: "add-notes",
      trackIndex: 0,
      patternIndex: 0,
      notes: [
        { tick: 0, gateTicks: STEP_TICKS, note: 60, velocity: 100 },
        { tick: STEP_TICKS, gateTicks: STEP_TICKS, note: 64, velocity: 96 },
      ],
    });

    const [first, second] = activeNotes();
    expect(activeNotes()).toHaveLength(2);
    expect(projectTracksWithStepData(get(projectStore)!)).toHaveLength(1);
    expect(projectPatternDataCount(get(projectStore)!)).toBe(1);
    expect(projectSummary(get(projectStore)!)).toContain("1 track");
    expect(first.id).toBe("t0:p0:n0");
    expect(second.id).toBe("t0:p0:n1");

    dispatchProjectEdit({
      type: "update-notes",
      trackIndex: 0,
      patternIndex: 0,
      patches: [
        {
          noteId: first.id,
          patch: {
            tick: STEP_TICKS * 2,
            gateTicks: STEP_TICKS * 2,
            note: 67,
          },
        },
      ],
    });

    const updated = activeNotes()[0];
    expect(updated.id).toBe(first.id);
    expect(updated.tick).toBe(STEP_TICKS * 2);
    expect(updated.gateTicks).toBe(STEP_TICKS * 2);
    expect(updated.note).toBe(67);
  });

  it("undoes and redoes note batches as single history entries", () => {
    dispatchProjectEdit({
      type: "add-notes",
      trackIndex: 0,
      patternIndex: 0,
      notes: [
        { tick: 0, gateTicks: STEP_TICKS, note: 60, velocity: 100 },
        { tick: STEP_TICKS, gateTicks: STEP_TICKS, note: 64, velocity: 96 },
      ],
    });

    expect(activeNotes()).toHaveLength(2);
    expect(get(editHistoryStore)).toMatchObject({
      undoDepth: 1,
      redoDepth: 0,
      canUndo: true,
      canRedo: false,
    });

    dispatchProjectEdit({
      type: "delete-notes",
      trackIndex: 0,
      patternIndex: 0,
      noteIds: activeNotes().map((note) => note.id),
    });

    expect(activeNotes()).toHaveLength(0);
    expect(get(editHistoryStore).undoDepth).toBe(2);

    undoProjectEdit();
    expect(activeNotes()).toHaveLength(2);
    expect(get(editHistoryStore)).toMatchObject({
      undoDepth: 1,
      redoDepth: 1,
      canUndo: true,
      canRedo: true,
    });

    redoProjectEdit();
    expect(activeNotes()).toHaveLength(0);
    expect(get(editHistoryStore)).toMatchObject({
      undoDepth: 2,
      redoDepth: 0,
      canUndo: true,
      canRedo: false,
    });
  });
});
