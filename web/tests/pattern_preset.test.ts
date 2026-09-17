import { describe, expect, it } from "vitest";
import { readFileSync } from "fs";
import {
  applyEdit,
  buildProjectViewModel,
} from "../src/lib/xy/projectViewModel";
import {
  buildArrangementFromBytes,
  ImageProject,
  trackStructTemplateFromBytes,
} from "../src/lib/xy/image_writer";
import { exportXYProjectBytes } from "../src/lib/xy/projectExporter";
import { loadXYBytes } from "../src/lib/xy/projectLoader";
import {
  opXyPresetById,
  opXyTrackStructFromDonor,
  resolvePatternPresetId,
  trackStructForPreset,
} from "../src/lib/xy/opXyPresets";
import {
  dispatchProjectEdit,
  projectStore,
  redoProjectEdit,
  undoProjectEdit,
} from "../src/stores/project";
import { get } from "svelte/store";

const BASELINE = "../src/one-off-changes-from-default/unnamed 1.xy";
const STRINGS_DONOR =
  "../src/factory-preset-captures/firmware-1.1.21/strings/whitness.xy";
const FP01_DONOR =
  "../src/factory-preset-captures/firmware-1.1.21/batches/fp01.xy";

function loadBaseline() {
  const bytes = new Uint8Array(readFileSync(BASELINE));
  return loadXYBytes(bytes, "unnamed 1.xy");
}

describe("pattern preset view model and edit bridge", () => {
  it("reads factory preset path and engine on baseline patterns", () => {
    const project = loadBaseline();
    const t1 = project.tracks[0].patterns[0];
    const t3 = project.tracks[2].patterns[0];
    const t4 = project.tracks[3].patterns[0];

    expect(t1.presetId).toBe("drum-boop");
    expect(t1.presetLabel).toBe("boop");

    expect(t3.presetId).toBe("bass-shoulder");
    expect(t3.presetLabel).toBe("shoulder");

    expect(t4.presetId).toBe("pluck-beach-bum");
    expect(t4.presetLabel).toBe("beach bum");
  });

  it("reads captured factory preset paths accurately", () => {
    const bytes = new Uint8Array(readFileSync(STRINGS_DONOR));
    const project = loadXYBytes(bytes, "whitness.xy");
    const t8p0 = project.tracks[7].patterns[0];

    expect(t8p0.presetId).toBe("strings-whitness");
    expect(t8p0.presetLabel).toBe("whitness");
  });

  it("resolves raw preset paths and provides sensible track defaults", () => {
    expect(resolvePatternPresetId("pluck/beach bum", 3)).toBe(
      "pluck-beach-bum",
    );
    expect(resolvePatternPresetId("strings/whitness", 7)).toBe(
      "strings-whitness",
    );
    expect(resolvePatternPresetId("bass/alloy", 0)).toBe("bass-alloy");
    // Fallbacks when empty or unmapped
    expect(resolvePatternPresetId("", 0)).toBe("drum-boop");
    expect(resolvePatternPresetId("", 2)).toBe("bass-shoulder");
    expect(resolvePatternPresetId("", 3)).toBe("pluck-beach-bum");
    expect(resolvePatternPresetId("/", 4)).toBe("lead-gaussian");
  });

  it("applies a preset to a pattern, preserves notes and timing, and round-trips via export", () => {
    const project = loadBaseline();
    const donorBytes = new Uint8Array(readFileSync(STRINGS_DONOR));
    const stringsPreset = opXyPresetById("strings-whitness")!;
    const donorStruct = opXyTrackStructFromDonor(stringsPreset, donorBytes);

    // Add a test note to Track 4 (index 3), Pattern 0
    const withNote = applyEdit(project, {
      type: "add-note",
      trackIndex: 3,
      patternIndex: 0,
      note: { note: 60, velocity: 100, step: 1, gateTicks: 480 },
    });

    const originalNoteCount = withNote.tracks[3].patterns[0].notes.length;
    expect(originalNoteCount).toBe(1);
    expect(withNote.tracks[3].patterns[0].presetId).toBe("pluck-beach-bum");

    // Change preset on Track 4, Pattern 0 to strings-whitness
    const edited = applyEdit(withNote, {
      type: "set-pattern-preset",
      trackIndex: 3,
      patternIndex: 0,
      presetId: "strings-whitness",
      donorStruct,
    });

    const editedPattern = edited.tracks[3].patterns[0];
    expect(editedPattern.presetId).toBe("strings-whitness");
    expect(editedPattern.presetLabel).toBe("whitness");
    expect(editedPattern.notes).toHaveLength(1);
    expect(editedPattern.notes[0].note).toBe(60);
    expect(editedPattern.totalSteps).toBe(16);
    expect(edited.modified).toBe(true);

    // Verify other tracks remained unaffected
    expect(edited.tracks[0].patterns[0].presetId).toBe("drum-boop");
    expect(edited.tracks[2].patterns[0].presetId).toBe("bass-shoulder");

    // Export and re-read: preset must be preserved
    const exportedBytes = exportXYProjectBytes(edited);
    const reloaded = loadXYBytes(exportedBytes, "exported.xy");
    const reloadedPattern = reloaded.tracks[3].patterns[0];
    expect(reloadedPattern.presetId).toBe("strings-whitness");
    expect(reloadedPattern.presetLabel).toBe("whitness");
    expect(reloadedPattern.notes).toHaveLength(1);
    expect(reloadedPattern.notes[0].note).toBe(60);
  });

  it("supports undo and redo through the project store", () => {
    const project = loadBaseline();
    projectStore.set(project);

    const donorBytes = new Uint8Array(readFileSync(STRINGS_DONOR));
    const stringsPreset = opXyPresetById("strings-whitness")!;
    const donorStruct = opXyTrackStructFromDonor(stringsPreset, donorBytes);

    expect(get(projectStore)?.tracks[3].patterns[0].presetId).toBe(
      "pluck-beach-bum",
    );

    dispatchProjectEdit({
      type: "set-pattern-preset",
      trackIndex: 3,
      patternIndex: 0,
      presetId: "strings-whitness",
      donorStruct,
    });

    expect(get(projectStore)?.tracks[3].patterns[0].presetId).toBe(
      "strings-whitness",
    );

    undoProjectEdit();
    expect(get(projectStore)?.tracks[3].patterns[0].presetId).toBe(
      "pluck-beach-bum",
    );

    redoProjectEdit();
    expect(get(projectStore)?.tracks[3].patterns[0].presetId).toBe(
      "strings-whitness",
    );
  });

  it("allows setting different presets per pattern on the same track", () => {
    const baselineBytes = new Uint8Array(readFileSync(BASELINE));
    // Build a project where Track 4 has 2 patterns
    const multiPatternBytes = buildArrangementFromBytes(baselineBytes, {
      4: [
        { notes: [{ step: 1, note: 60 }] },
        { notes: [{ step: 5, note: 64 }] },
      ],
    });

    const project = loadXYBytes(multiPatternBytes, "multi.xy");
    expect(project.tracks[3].patterns).toHaveLength(2);

    const donorBytes = new Uint8Array(readFileSync(STRINGS_DONOR));
    const stringsPreset = opXyPresetById("strings-whitness")!;
    const donorStruct = opXyTrackStructFromDonor(stringsPreset, donorBytes);

    // Apply strings preset ONLY to pattern 1 (index 1), keeping pattern 0 as beach bum
    const edited = applyEdit(project, {
      type: "set-pattern-preset",
      trackIndex: 3,
      patternIndex: 1,
      presetId: "strings-whitness",
      donorStruct,
    });

    expect(edited.tracks[3].patterns[0].presetId).toBe("pluck-beach-bum");
    expect(edited.tracks[3].patterns[1].presetId).toBe("strings-whitness");

    // Export and reload: verify per-pattern preset independence
    const exportedBytes = exportXYProjectBytes(edited);
    const reloaded = loadXYBytes(exportedBytes, "multi-exported.xy");
    expect(reloaded.tracks[3].patterns[0].presetId).toBe("pluck-beach-bum");
    expect(reloaded.tracks[3].patterns[1].presetId).toBe("strings-whitness");
  });

  it("applies a preset across all patterns on a track with set-track-preset and persists across scenes", () => {
    const baselineBytes = new Uint8Array(readFileSync(BASELINE));
    // Build a project where Track 4 has 3 patterns
    const multiPatternBytes = buildArrangementFromBytes(baselineBytes, {
      4: [
        { notes: [{ step: 1, note: 60 }] },
        { notes: [{ step: 5, note: 64 }] },
        { notes: [{ step: 9, note: 67 }] },
      ],
    });

    const project = loadXYBytes(multiPatternBytes, "multi.xy");
    expect(project.tracks[3].patterns).toHaveLength(3);
    expect(project.tracks[3].patterns[0].presetId).toBe("pluck-beach-bum");
    expect(project.tracks[3].patterns[1].presetId).toBe("pluck-beach-bum");
    expect(project.tracks[3].patterns[2].presetId).toBe("pluck-beach-bum");

    const donorBytes = new Uint8Array(readFileSync(STRINGS_DONOR));
    const stringsPreset = opXyPresetById("strings-whitness")!;
    const donorStruct = opXyTrackStructFromDonor(stringsPreset, donorBytes);

    // Apply strings preset to the ENTIRE track
    const edited = applyEdit(project, {
      type: "set-track-preset",
      trackIndex: 3,
      presetId: "strings-whitness",
      donorStruct,
    });

    // Verify all 3 patterns received the strings preset
    expect(edited.tracks[3].patterns[0].presetId).toBe("strings-whitness");
    expect(edited.tracks[3].patterns[1].presetId).toBe("strings-whitness");
    expect(edited.tracks[3].patterns[2].presetId).toBe("strings-whitness");

    // Notes and timings preserved on all patterns
    expect(edited.tracks[3].patterns[0].notes[0].note).toBe(60);
    expect(edited.tracks[3].patterns[1].notes[0].note).toBe(64);
    expect(edited.tracks[3].patterns[2].notes[0].note).toBe(67);

    // Other tracks unaffected
    expect(edited.tracks[0].patterns[0].presetId).toBe("drum-boop");
    expect(edited.tracks[2].patterns[0].presetId).toBe("bass-shoulder");

    // Roundtrip export and reload
    const exportedBytes = exportXYProjectBytes(edited);
    const reloaded = loadXYBytes(exportedBytes, "track-preset-exported.xy");
    expect(reloaded.tracks[3].patterns[0].presetId).toBe("strings-whitness");
    expect(reloaded.tracks[3].patterns[1].presetId).toBe("strings-whitness");
    expect(reloaded.tracks[3].patterns[2].presetId).toBe("strings-whitness");
    expect(reloaded.tracks[3].patterns[0].notes[0].note).toBe(60);
    expect(reloaded.tracks[3].patterns[1].notes[0].note).toBe(64);
    expect(reloaded.tracks[3].patterns[2].notes[0].note).toBe(67);
  });

  it("applies OP-XY device samples to a track and embeds the device path in the binary project", () => {
    const project = loadBaseline();
    const edited = applyEdit(project, {
      type: "apply-device-sample",
      trackIndex: 0,
      sampleName: "808_Kick",
      samplePath: "/samples/user/drums/808_Kick.wav",
      isDrum: true,
    });

    const exportedBytes = exportXYProjectBytes(edited);
    const reloaded = loadXYBytes(exportedBytes, "device-sample-exported.xy");

    expect(reloaded.tracks[0].patterns[0].engineId).toBe(3);
    expect(reloaded.tracks[0].patterns[0].presetPath).toBe(
      "/samples/user/drums/808_Kick.wav",
    );
  });
});
