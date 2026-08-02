import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  OP_XY_FACTORY_CATEGORIES,
  OP_XY_FACTORY_PRESET_CATALOG,
  OP_XY_FACTORY_PRESET_NAMES,
  OP_XY_PRESET_CHOICES,
  opXyPresetById,
  opXyTrackStructFromDonor,
  recommendedOpXyPresetId,
} from "../src/lib/xy/opXyPresets";
import { trackStructTemplateFromBytes } from "../src/lib/xy/image_writer";

function readString(bytes: Uint8Array, offset: number, capacity: number) {
  const field = bytes.subarray(offset, offset + capacity);
  const end = field.indexOf(0);
  return new TextDecoder().decode(end >= 0 ? field.subarray(0, end) : field);
}

describe("OP-XY preset catalog", () => {
  it("uses only the factory shipping preset folders", () => {
    expect(OP_XY_FACTORY_CATEGORIES).toEqual([
      "bass",
      "drum",
      "keys",
      "lead",
      "organ",
      "pad",
      "pluck",
      "strings",
    ]);
    for (const preset of OP_XY_PRESET_CHOICES) {
      expect(OP_XY_FACTORY_CATEGORIES).toContain(preset.category);
    }
  });

  it("contains no third-party nt presets", () => {
    for (const preset of OP_XY_PRESET_CHOICES) {
      expect(preset.id).not.toMatch(/^nt-/i);
      expect(preset.label).not.toMatch(/^nt-/i);
    }
  });

  it("contains the complete firmware 1.1.21 factory-name catalogue", () => {
    expect(OP_XY_FACTORY_PRESET_CATALOG).toHaveLength(156);
    expect(
      Object.fromEntries(
        OP_XY_FACTORY_CATEGORIES.map((category) => [
          category,
          OP_XY_FACTORY_PRESET_NAMES[category].length,
        ]),
      ),
    ).toEqual({
      bass: 28,
      drum: 12,
      keys: 26,
      lead: 27,
      organ: 11,
      pad: 22,
      pluck: 23,
      strings: 7,
    });

    const ids = OP_XY_FACTORY_PRESET_CATALOG.map((preset) => preset.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(OP_XY_FACTORY_PRESET_NAMES.keys).toContain("elect piano");
    expect(OP_XY_FACTORY_PRESET_NAMES.organ).toContain("dusty org");
    expect(OP_XY_FACTORY_PRESET_NAMES.strings).toContain("nachtmusik");
  });

  it("only marks byte-validated sound templates as selectable", () => {
    expect(
      OP_XY_FACTORY_PRESET_CATALOG.filter((preset) => preset.available)
        .map((preset) => preset.id)
        .sort(),
    ).toEqual(OP_XY_PRESET_CHOICES.map((preset) => preset.id).sort());
  });

  it("makes every factory Strings preset selectable", () => {
    expect(
      OP_XY_FACTORY_PRESET_CATALOG.filter(
        (preset) => preset.category === "strings" && preset.available,
      ).map((preset) => preset.label),
    ).toEqual([...OP_XY_FACTORY_PRESET_NAMES.strings]);
  });

  it("maps the Golden Brown harpsichord program to a plucked device preset", () => {
    expect(recommendedOpXyPresetId(6, "chord", false)).toBe("pluck-dielectric");
  });

  it("preserves captured donor labels and sample paths byte-exact", () => {
    const donor = new Uint8Array(
      readFileSync("../src/presets/presetprojs/nt-grand piano.xy"),
    );
    const expected = trackStructTemplateFromBytes(donor);
    const track = opXyTrackStructFromDonor(donor);

    expect(track).toEqual(expected);
    expect(readString(track, 0x453f, 48)).toBe("1/nt-grand piano");
    expect(readString(track, 0x395f, 72)).toContain(
      "/fat32/presets/1/nt-grand piano.preset/",
    );
  });

  it.each([
    ["strings-ensemble", "ensemble"],
    ["strings-intimate-str", "intimate str"],
    ["strings-nachtmusik", "nachtmusik"],
    ["strings-pointe", "pointe"],
    ["strings-soutenu", "soutenu"],
    ["strings-whitness", "whitness"],
  ])("extracts the Track 8 sound state for %s", (id, label) => {
    const preset = opXyPresetById(id);
    expect(preset).toBeDefined();
    const donor = new Uint8Array(
      readFileSync(
        `../src/factory-preset-captures/firmware-1.1.21/strings/${label}.xy`,
      ),
    );
    const expected = trackStructTemplateFromBytes(donor, 8);
    const track = opXyTrackStructFromDonor(preset!, donor);

    expect(track).toEqual(expected);
    expect(track).not.toEqual(trackStructTemplateFromBytes(donor, 1));
    expect(readString(track, 0x453f, 48)).toBe(`strings/${label}`);
  });
});
