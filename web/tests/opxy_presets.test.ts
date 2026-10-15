import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  OP_XY_FACTORY_CATEGORIES,
  OP_XY_FACTORY_PRESET_CAPTURES,
  OP_XY_FACTORY_PRESET_CATALOG,
  OP_XY_FACTORY_PRESET_NAMES,
  OP_XY_PRESET_CHOICES,
  opXyPresetById,
  opXyTrackStructFromDonor,
  recommendedOpXyPresetId,
} from "../src/lib/xy/opXyPresets";
import { trackStructTemplateFromBytes } from "../src/lib/xy/image_writer";
import captureManifest from "../src/lib/xy/opXyFactoryPresetCaptureManifest.json";

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
      "drumline",
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

  it("contains the proven catalogue plus the firmware 1.2.0 Drumline names", () => {
    expect(OP_XY_FACTORY_PRESET_CATALOG).toHaveLength(165);
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
      drumline: 9,
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
    expect(OP_XY_FACTORY_PRESET_NAMES.drumline).toEqual([
      "atom",
      "beatnic",
      "cinortcele",
      "dote yet",
      "helpline",
      "macaroni",
      "that tom tom tom",
      "tyche",
      "we will c",
    ]);
  });

  it("makes every byte-validated factory preset selectable", () => {
    expect(OP_XY_PRESET_CHOICES).toHaveLength(165);
    expect(
      OP_XY_FACTORY_PRESET_CATALOG.every((preset) => preset.available),
    ).toBe(true);
    expect(
      OP_XY_FACTORY_PRESET_CATALOG.filter((preset) => preset.available)
        .map((preset) => preset.id)
        .sort(),
    ).toEqual(OP_XY_PRESET_CHOICES.map((preset) => preset.id).sort());
  });

  it("makes every device-authored Drumline preset selectable", () => {
    expect(
      OP_XY_FACTORY_PRESET_CATALOG.filter(
        (preset) => preset.category === "drumline",
      ).every((preset) => preset.available),
    ).toBe(true);
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

  it("maps all 157 captured factory sounds to pristine device donor tracks", () => {
    expect(OP_XY_FACTORY_PRESET_CAPTURES).toHaveLength(157);
    expect(
      new Set(OP_XY_FACTORY_PRESET_CAPTURES.map(({ id }) => id)).size,
    ).toBe(157);

    for (const file of captureManifest.files) {
      const firmware =
        "firmware" in file ? file.firmware : captureManifest.firmware;
      const donor = new Uint8Array(
        readFileSync(
          `../src/factory-preset-captures/firmware-${firmware}/${file.source}`,
        ),
      );
      for (const [trackText, [category, label]] of Object.entries(
        file.tracks,
      )) {
        const donorTrack = Number(trackText);
        const capture = OP_XY_FACTORY_PRESET_CAPTURES.find(
          (candidate) =>
            candidate.donorFile === file.asset &&
            candidate.donorTrack === donorTrack,
        );
        expect(capture).toMatchObject({ category, label, donorTrack });
        const preset = opXyPresetById(capture!.id);
        expect(preset).toBeDefined();
        const track = opXyTrackStructFromDonor(preset!, donor);

        expect(track).toEqual(trackStructTemplateFromBytes(donor, donorTrack));
        expect(track[0]).toBe(1);
        expect(track[0x456f]).toBe(0);
        expect(readString(track, 0x453f, 48)).toBe(`${category}/${label}`);
      }
    }
  }, 15_000);

  it("shares 26 donor projects instead of fetching one file per preset", () => {
    const donorUrls = OP_XY_PRESET_CHOICES.flatMap((preset) =>
      preset.donorUrl ? [preset.donorUrl] : [],
    );

    expect(donorUrls).toHaveLength(157);
    expect(new Set(donorUrls).size).toBe(26);
    expect(captureManifest.files).toHaveLength(26);
  });
});
