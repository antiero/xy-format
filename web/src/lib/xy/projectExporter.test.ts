import { describe, expect, it } from "vitest";
import { normalizeXYFileName, xyProjectName } from "./projectExporter";

describe("OP-XY project filenames", () => {
  it("always writes the required .xy extension", () => {
    expect(normalizeXYFileName("my project.xyzka")).toBe("my project.xyzka.xy");
    expect(normalizeXYFileName("my project.XY")).toBe("my project.xy");
  });

  it("exposes only the project name for editing", () => {
    expect(xyProjectName("my project.xy")).toBe("my project");
    expect(xyProjectName("my project.XY")).toBe("my project");
  });
});
