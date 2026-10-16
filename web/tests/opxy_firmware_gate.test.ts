import { readFileSync } from "fs";
import { describe, expect, it } from "vitest";
import { decodeProject } from "../src/lib/xy/rle";
import {
  donorFitsTarget,
  donorsForTarget,
  opXyPresetById,
  PresetFirmwareError,
  trackStructForPreset,
  xyFirmwareFamily,
} from "../src/lib/xy/opXyPresets";

const read = (path: string) => new Uint8Array(readFileSync(path));
const OLD = read("../src/one-off-changes-from-default/unnamed 1.xy");
const FP01 = read(
  "../src/factory-preset-captures/firmware-1.1.21/batches/fp01.xy",
);
const DRUMLINE = read(
  "../src/factory-preset-captures/firmware-1.2.0/batches/drumline01.xy",
);

describe("donor firmware gate", () => {
  it("reads the firmware family from header byte 5", () => {
    expect(xyFirmwareFamily(OLD)).toBe(0x13);
    expect(xyFirmwareFamily(FP01)).toBe(0x13);
    expect(xyFirmwareFamily(DRUMLINE)).toBe(0x14);
    expect(xyFirmwareFamily(decodeProject(DRUMLINE).header)).toBe(0x14);
  });

  it("allows same-or-older family donors and blocks newer ones", () => {
    const oldHeader = decodeProject(OLD).header;
    const newHeader = decodeProject(DRUMLINE).header;
    expect(donorFitsTarget(FP01, oldHeader)).toBe(true);
    expect(donorFitsTarget(DRUMLINE, oldHeader)).toBe(false);
    expect(donorFitsTarget(DRUMLINE, newHeader)).toBe(true);
    expect(donorFitsTarget(FP01, newHeader)).toBe(true);
    expect(
      Object.keys(donorsForTarget({ a: FP01, b: DRUMLINE }, oldHeader)),
    ).toEqual(["a"]);
  });

  it("refuses to splice a Drumline donor into an old-header project", () => {
    const preset = opXyPresetById("drumline-atom");
    expect(preset).toBeDefined();
    const donors = { "drumline-atom": DRUMLINE };
    expect(() =>
      trackStructForPreset(
        preset!,
        donors,
        undefined,
        decodeProject(OLD).header,
      ),
    ).toThrow(PresetFirmwareError);
    expect(
      trackStructForPreset(
        preset!,
        donors,
        undefined,
        decodeProject(DRUMLINE).header,
      ),
    ).toHaveLength(17876);
  });
});
