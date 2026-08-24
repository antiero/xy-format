import { describe, expect, it } from "vitest";
import { readFileSync } from "fs";
import {
  applyEdit,
  buildProjectViewModel,
} from "../src/lib/xy/projectViewModel";
import {
  buildArrangementFromBytes,
  ImageProject,
} from "../src/lib/xy/image_writer";
import { exportXYProjectBytes } from "../src/lib/xy/projectExporter";
import { loadXYBytes } from "../src/lib/xy/projectLoader";

const BASELINE = "../src/one-off-changes-from-default/unnamed 1.xy";
const TWO_SCENES =
  "../src/scene-probes/2026-06-volumes/s0b-baseline-2scenes.xy";
const SONG_TWO = "../src/one-off-changes-from-default/unnamed 155.xy";

function loadBaseline() {
  const bytes = new Uint8Array(readFileSync(BASELINE));
  return loadXYBytes(bytes, "unnamed 1.xy");
}

describe("project view model and edit bridge", () => {
  it("loads a real .xy project into tracks, patterns, scenes, and Song 1", () => {
    const project = loadBaseline();
    expect(project.tracks).toHaveLength(16);
    expect(project.tempoBpm).toBeGreaterThan(0);
    expect(project.tracks[0].patterns.length).toBeGreaterThanOrEqual(1);
    expect(project.tracks[0].patterns[0]).toMatchObject({
      totalSteps: 16,
      bars: 1,
      finalBarSteps: 16,
      trackScale: "1",
    });
    expect(project.scenes).toHaveLength(99);
    expect(project.songs).toHaveLength(14);
    expect(project.songs[0]).toMatchObject({
      supported: true,
      sceneChain: [0],
      loop: true,
    });
  });

  it("reads and writes all 14 serialized song slots", () => {
    const captured = loadXYBytes(
      new Uint8Array(readFileSync(SONG_TWO)),
      "song-two.xy",
    );
    expect(captured.songs[1]).toMatchObject({
      index: 1,
      sceneChain: [0, 1, 2],
      loop: true,
      supported: true,
    });

    const edited = applyEdit(loadBaseline(), {
      type: "update-song-chain",
      songIndex: 13,
      sceneChain: [0, 1, 2],
      loop: true,
    });
    const reloaded = loadXYBytes(exportXYProjectBytes(edited), "song-14.xy");
    expect(reloaded.songs[13]).toMatchObject({
      index: 13,
      sceneChain: [0, 1, 2],
      loop: true,
      supported: true,
    });
    expect(reloaded.songs[0].sceneChain).toEqual([0]);
  });

  it("edits notes and pattern length, then exports and reloads the changes", () => {
    let project = loadBaseline();
    project = applyEdit(project, {
      type: "add-note",
      trackIndex: 0,
      patternIndex: 0,
      note: { tick: 0, gateTicks: 480, note: 60, velocity: 90 },
    });
    const noteId = project.tracks[0].patterns[0].notes[0].id;
    project = applyEdit(project, {
      type: "update-note",
      trackIndex: 0,
      patternIndex: 0,
      noteId,
      patch: { note: 62, velocity: 77 },
    });
    project = applyEdit(project, {
      type: "set-pattern-steps",
      trackIndex: 0,
      patternIndex: 0,
      steps: 24,
    });

    const reloaded = loadXYBytes(exportXYProjectBytes(project), "roundtrip.xy");
    expect(reloaded.tracks[0].patterns[0].totalSteps).toBe(24);
    expect(reloaded.tracks[0].patterns[0].notes).toHaveLength(1);
    expect(reloaded.tracks[0].patterns[0].notes[0]).toMatchObject({
      note: 62,
      velocity: 77,
    });
  });

  it("stores an edited tempo in the exported project within OP-XY limits", () => {
    let project = applyEdit(loadBaseline(), { type: "set-tempo", bpm: 1 });
    expect(project.tempoBpm).toBe(40);

    project = applyEdit(project, {
      type: "set-tempo",
      bpm: 137.4,
    });
    expect(project.tempoBpm).toBe(137.4);
    expect(project.modified).toBe(true);

    project = applyEdit(project, { type: "set-tempo", bpm: 999 });
    expect(project.tempoBpm).toBe(220);

    const reloaded = loadXYBytes(exportXYProjectBytes(project), "tempo.xy");
    expect(reloaded.tempoBpm).toBe(220);
  });

  it("edits scene pattern/mute state and Song 1 chain", () => {
    let project = loadBaseline();
    project = applyEdit(project, {
      type: "set-scene-pattern",
      sceneIndex: 0,
      trackIndex: 0,
      patternIndex: 0,
    });
    project = applyEdit(project, {
      type: "set-scene-mute",
      sceneIndex: 0,
      trackIndex: 1,
      muted: true,
    });
    project = applyEdit(project, {
      type: "update-song-chain",
      songIndex: 0,
      sceneChain: [0, 1, 2],
      loop: false,
    });

    const reloaded = loadXYBytes(exportXYProjectBytes(project), "arranged.xy");
    expect(reloaded.scenes[0].patternByTrack[0]).toBe(0);
    expect(reloaded.scenes[0].mutedTracks[1]).toBe(true);
    expect(reloaded.songs[0]).toMatchObject({
      sceneChain: [0, 1, 2],
      loop: false,
      supported: true,
    });
  });

  it("maps device-authored Scene N directly to physical row N-1", () => {
    const project = loadXYBytes(
      new Uint8Array(readFileSync(TWO_SCENES)),
      "two-scenes.xy",
    );

    expect(project.scenes[0].present).toBe(true);
    expect(project.scenes[0].patternByTrack.slice(0, 4)).toEqual([0, 0, 0, 0]);
    expect(project.scenes[1].present).toBe(true);
    expect(project.scenes[1].patternByTrack.slice(0, 4)).toEqual([1, 0, 0, 0]);
    expect(project.scenes[2].present).toBe(false);
  });

  it("validates scene references that exceed available patterns", () => {
    const imageProject = ImageProject.fromBytes(
      new Uint8Array(readFileSync(BASELINE)),
    );
    imageProject.setScenePattern(0, 1, 8);
    const project = buildProjectViewModel(imageProject, "bad-scene.xy");
    expect(
      project.validation.some(
        (issue) => issue.code === "scene-missing-pattern",
      ),
    ).toBe(true);
  });

  it("reads observed scale-4 byte without falling back to unknown timing", () => {
    const imageProject = ImageProject.fromBytes(
      new Uint8Array(readFileSync(BASELINE)),
    );
    imageProject.setTrackScaleRaw(1, 0x07, 0);
    const project = buildProjectViewModel(imageProject, "scale-4.xy");
    expect(project.tracks[0].patterns[0]).toMatchObject({
      trackScale: "4",
      trackScaleLabel: "4",
      trackScaleKnown: true,
      trackScaleWriteSupported: true,
      effectiveLength16ths: 64,
    });
    expect(
      project.validation.some((issue) => issue.code === "track-scale-unknown"),
    ).toBe(false);
  });

  it("writes firmware 1.1.25 odd track-scale bytes", () => {
    const scale3 = applyEdit(loadBaseline(), {
      type: "set-track-scale",
      trackIndex: 0,
      patternIndex: 0,
      scale: "3",
    });
    const scale7 = applyEdit(scale3, {
      type: "set-track-scale",
      trackIndex: 0,
      patternIndex: 0,
      scale: "7",
    });

    expect(scale3.tracks[0].patterns[0].trackScaleRaw).toBe(0x06);
    expect(scale7.tracks[0].patterns[0]).toMatchObject({
      trackScale: "7",
      trackScaleRaw: 0x0a,
      trackScaleWriteSupported: true,
    });
  });

  it("rotates triggers, p-lock rows and component rows together", () => {
    const bytes = new Uint8Array(readFileSync(BASELINE));
    const imageProject = ImageProject.fromBytes(bytes);
    imageProject.setPatternSteps(1, 4, 0);
    imageProject.addNote(1, { step: 1, note: 60, patternIndex: 0 });
    imageProject.addNote(1, { step: 4, note: 64, patternIndex: 0 });
    const base = imageProject.trackPatternStart(1, 0);
    imageProject.image[base + 0x02a0] = 0x11;
    imageProject.image[base + 0x02a0 + 3 * 84] = 0x44;
    imageProject.image[base + 0x2c4e] = 1;
    imageProject.image[base + 0x2c4e + 3 * 8] = 4;
    imageProject.image[base + 0x3057] = 0xa1;
    imageProject.image[base + 0x3057 + 3 * 16] = 0xd4;
    const inactiveBefore = imageProject.image.slice(
      base + 0x3057 + 4 * 16,
      base + 0x3057 + 5 * 16,
    );

    imageProject.rotatePatternSteps(1, 1, 0);

    expect(
      imageProject.getNotes(1, 0).map((note) => [note.tick, note.note]),
    ).toEqual([
      [0, 64],
      [480, 60],
    ]);
    expect(imageProject.image[base + 0x02a0]).toBe(0x44);
    expect(imageProject.image[base + 0x02a0 + 84]).toBe(0x11);
    expect(imageProject.image[base + 0x2c4e]).toBe(4);
    expect(imageProject.image[base + 0x2c4e + 8]).toBe(1);
    expect(imageProject.image[base + 0x3057]).toBe(0xd4);
    expect(imageProject.image[base + 0x3057 + 16]).toBe(0xa1);
    expect(
      imageProject.image.slice(base + 0x3057 + 4 * 16, base + 0x3057 + 5 * 16),
    ).toEqual(inactiveBefore);
  });

  it("preserves opaque player state when constructing pattern clones", () => {
    const baseline = ImageProject.fromBytes(
      new Uint8Array(readFileSync(BASELINE)),
    );
    const opaqueOffset = 0x0100;
    baseline.image[baseline.trackPatternStart(1, 0) + opaqueOffset] = 0x5a;

    const arranged = buildArrangementFromBytes(baseline.toBytes(), {
      1: [[], []],
    });
    const reloaded = ImageProject.fromBytes(arranged);
    expect(
      reloaded.image[reloaded.trackPatternStart(1, 0) + opaqueOffset],
    ).toBe(0x5a);
    expect(
      reloaded.image[reloaded.trackPatternStart(1, 1) + opaqueOffset],
    ).toBe(0x5a);
  });
});
