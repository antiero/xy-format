import { readFileSync } from "fs";
import { describe, expect, it } from "vitest";
import { ImageProject } from "../src/lib/xy/image_writer";
import {
  GLOBAL_SCENE_LENGTH,
  GLOBAL_TIME_SIGNATURE,
  SCENE_LENGTH_NAMES,
  TIME_SIGNATURE_NAMES,
  projectTimeSignatureRaw,
  sceneLengthName,
  timeSignatureName,
} from "../src/lib/xy/projectConfig";

const BASELINE = "../src/one-off-changes-from-default/unnamed 1.xy";

function baselineProject(): ImageProject {
  return ImageProject.fromBytes(new Uint8Array(readFileSync(BASELINE)));
}

describe("OP-XY project time-signature parity", () => {
  it("reads the baseline fields and decoded names", () => {
    const project = baselineProject();

    expect(project.getSceneLengthMode()).toBe(0);
    expect(project.getTimeSignatureRaw()).toBe(0x11);
    expect(sceneLengthName(project.getSceneLengthMode())).toBe("longest");
    expect(timeSignatureName(project.getTimeSignatureRaw())).toBe("4/4");
  });

  it.each(Object.entries(SCENE_LENGTH_NAMES))(
    "writes Python scene-length enum %s (%s)",
    (raw, name) => {
      const project = baselineProject();
      project.setSceneLengthMode(Number(raw));

      expect(project.image[GLOBAL_SCENE_LENGTH]).toBe(Number(raw));
      expect(sceneLengthName(project.getSceneLengthMode())).toBe(name);
    },
  );

  it.each(Object.entries(TIME_SIGNATURE_NAMES))(
    "writes Python time-signature enum %s (%s)",
    (raw, name) => {
      const project = baselineProject();
      project.setTimeSignature(Number(raw));
      const reloaded = ImageProject.fromBytes(project.toBytes());

      expect(project.image[GLOBAL_TIME_SIGNATURE]).toBe(Number(raw));
      expect(reloaded.getTimeSignatureRaw()).toBe(Number(raw));
      expect(timeSignatureName(reloaded.getTimeSignatureRaw())).toBe(name);
      const [numerator, denominator] = name.split("/").map(Number);
      expect(projectTimeSignatureRaw(numerator, denominator)).toBe(Number(raw));
    },
  );

  it("rejects values outside the Python writer enums", () => {
    const project = baselineProject();

    expect(() => project.setSceneLengthMode(3)).toThrow(
      "scene length mode must be 0=longest, 1=shortest, 2=time signature",
    );
    expect(() => project.setTimeSignature(0x16)).toThrow(
      "time signature raw enum must be 0x10..0x15",
    );
    expect(projectTimeSignatureRaw(2, 4)).toBeNull();
    expect(sceneLengthName(0xff)).toBe("unknown-0xFF");
    expect(timeSignatureName(0xff)).toBe("unknown-0xFF");
  });
});
