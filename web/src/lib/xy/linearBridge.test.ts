import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  applyLinearSequencePresets,
  buildLinearSequenceProject,
  exportActiveSongData,
  presetCatalogJSON,
} from "./linearBridge";
import { OP_XY_FACTORY_PRESET_CATALOG } from "./opXyPresets";
import { trackStructTemplateFromBytes } from "./image_writer";

const BLANK = new Uint8Array(
  readFileSync(new URL("../../../public/baselines/blank.xy", import.meta.url)),
);

function project() {
  return buildLinearSequenceProject(BLANK, {
    sceneCount: 1,
    notes: [
      {
        scene: 0,
        track: 2,
        step: 1,
        tick: 0,
        note: 48,
        velocity: 100,
        length: 1,
      },
    ],
  });
}

describe("linear bridge presets", () => {
  it("exports each pattern's preset id, label and category", () => {
    const exported = JSON.parse(exportActiveSongData(project()));
    const pattern = exported.tracks[2].patterns[0];
    expect(typeof pattern.presetId).toBe("string");
    expect(typeof pattern.presetLabel).toBe("string");
    expect(pattern).toHaveProperty("presetCategory");
  });

  it("applies requested presets with the track preset edit and reports failures", async () => {
    const loaded: string[] = [];
    const loadStruct = async (presetId: string) => {
      if (presetId === "missing") throw new Error("unknown preset id missing");
      loaded.push(presetId);
      return trackStructTemplateFromBytes(BLANK, 3);
    };
    const { skipped } = await applyLinearSequencePresets(
      project(),
      { "2": "bass-shoulder", "5": "missing", "12": "pad-bandpasser" },
      loadStruct,
    );
    expect(loaded).toEqual(["bass-shoulder"]);
    expect(skipped).toEqual(["missing"]);
  });

  it("serves the same catalogue as the web preset picker", () => {
    expect(JSON.parse(presetCatalogJSON())).toEqual(
      OP_XY_FACTORY_PRESET_CATALOG,
    );
  });
});
