import { describe, expect, it } from "vitest";
import { readFileSync } from "fs";
import {
  applyEdit,
  buildProjectViewModel,
} from "../src/lib/xy/projectViewModel";
import { ImageProject } from "../src/lib/xy/image_writer";
import { exportXYProjectBytes } from "../src/lib/xy/projectExporter";
import { loadXYBytes } from "../src/lib/xy/projectLoader";

const BASELINE = "../src/one-off-changes-from-default/unnamed 1.xy";

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
    expect(project.songs[0]).toMatchObject({
      supported: true,
      sceneChain: [0],
      loop: false,
    });
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

  it("reads observed scale-3 byte without falling back to unknown timing", () => {
    const imageProject = ImageProject.fromBytes(
      new Uint8Array(readFileSync(BASELINE)),
    );
    imageProject.setTrackScaleRaw(1, 0x07, 0);
    const project = buildProjectViewModel(imageProject, "scale-3.xy");
    expect(project.tracks[0].patterns[0]).toMatchObject({
      trackScale: "3",
      trackScaleLabel: "3",
      trackScaleKnown: true,
      trackScaleWriteSupported: false,
      effectiveLength16ths: 48,
    });
    expect(
      project.validation.some((issue) => issue.code === "track-scale-unknown"),
    ).toBe(false);
  });

  it("blocks track-scale writes whose raw bytes are not decoded", () => {
    const project = loadBaseline();
    expect(() =>
      applyEdit(project, {
        type: "set-track-scale",
        trackIndex: 0,
        patternIndex: 0,
        scale: "4",
      }),
    ).toThrow(/read-only/);
    expect(() =>
      applyEdit(project, {
        type: "set-track-scale",
        trackIndex: 0,
        patternIndex: 0,
        scale: "3",
      }),
    ).toThrow(/read-only/);
  });
});
