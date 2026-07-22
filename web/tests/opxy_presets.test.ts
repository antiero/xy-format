import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  OP_XY_PRESET_CHOICES,
  opXyTrackStructFromDonor,
  recommendedOpXyPresetId,
} from "../src/lib/xy/opXyPresets";

function readString(bytes: Uint8Array, offset: number, capacity: number) {
  const field = bytes.subarray(offset, offset + capacity);
  const end = field.indexOf(0);
  return new TextDecoder().decode(end >= 0 ? field.subarray(0, end) : field);
}

describe("OP-XY preset catalog", () => {
  it("maps the Golden Brown harpsichord program to a plucked device preset", () => {
    expect(recommendedOpXyPresetId(6, "chord", false)).toBe("nt-harpsicord");
  });

  it("rehomes every captured donor into its device library group", () => {
    for (const preset of OP_XY_PRESET_CHOICES) {
      if (!preset.donorUrl) continue;
      const donor = new Uint8Array(
        readFileSync(`../src/presets/presetprojs/${preset.label}.xy`),
      );
      const track = opXyTrackStructFromDonor(preset, donor);
      expect(readString(track, 0x453f, 48)).toBe(preset.presetPath);

      const samplePath = readString(track, 0x395f, 72);
      if (samplePath) {
        expect(samplePath).not.toContain("/presets/1/");
        expect(samplePath).toContain(`/presets/${preset.category}/`);
      }
    }
  });
});
