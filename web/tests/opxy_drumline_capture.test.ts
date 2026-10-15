import { existsSync, readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { loadXYBytes } from "../src/lib/xy/projectLoader";

const FIRST_DONOR =
  "../src/factory-preset-captures/firmware-1.2.0/batches/drumline01.xy";
const SECOND_DONOR =
  "../src/factory-preset-captures/firmware-1.2.0/batches/drumline02.xy";
const EXPECTED = [
  "atom",
  "beatnic",
  "cinortcele",
  "dote yet",
  "helpline",
  "macaroni",
  "that tom tom tom",
  "tyche",
] as const;

describe.skipIf(!existsSync(FIRST_DONOR))(
  "firmware 1.2.0 Drumline primary capture",
  () => {
    it("contains eight pristine device-authored donor tracks", () => {
      const bytes = new Uint8Array(readFileSync(FIRST_DONOR));
      const project = loadXYBytes(bytes, "drumline01.xy");

      expect(project.tracks).toHaveLength(16);
      for (const [trackIndex, label] of EXPECTED.entries()) {
        const track = project.tracks[trackIndex];
        expect(track.patterns).toHaveLength(1);
        expect(track.patterns[0].notes).toHaveLength(0);
        expect(track.patterns[0].presetId).toBe(
          `drumline-${label.replaceAll(" ", "-")}`,
        );
        expect(track.patterns[0].presetPath).toBe(`drumline/${label}`);
      }
    });
  },
);

describe.skipIf(!existsSync(SECOND_DONOR))(
  "firmware 1.2.0 Drumline final capture",
  () => {
    it("contains pristine we will c donors on Tracks 1–8", () => {
      const bytes = new Uint8Array(readFileSync(SECOND_DONOR));
      const project = loadXYBytes(bytes, "drumline02.xy");

      expect(project.tracks).toHaveLength(16);
      for (const track of project.tracks.slice(0, 8)) {
        expect(track.patterns).toHaveLength(1);
        expect(track.patterns[0].notes).toHaveLength(0);
        expect(track.patterns[0].presetId).toBe("drumline-we-will-c");
        expect(track.patterns[0].presetPath).toBe("drumline/we will c");
      }
    });
  },
);
