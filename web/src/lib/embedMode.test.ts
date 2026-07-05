import { describe, expect, it } from "vitest";
import { isXYBuddyNativeEmbed } from "./embedMode";

describe("isXYBuddyNativeEmbed", () => {
  it("returns false for a normal browser context", () => {
    expect(isXYBuddyNativeEmbed({ search: "", userAgent: "Safari" })).toBe(
      false,
    );
  });

  it("detects the preferred macOS embed query parameter", () => {
    expect(
      isXYBuddyNativeEmbed({
        search: "?embed=macos",
        userAgent: "Safari",
      }),
    ).toBe(true);
  });

  it("detects the alternate app query parameter", () => {
    expect(
      isXYBuddyNativeEmbed({
        search: "?xybuddyApp=1",
        userAgent: "Safari",
      }),
    ).toBe(true);
  });

  it("detects an injected native app global", () => {
    expect(
      isXYBuddyNativeEmbed({
        search: "",
        userAgent: "Safari",
        nativeAppGlobal: true,
      }),
    ).toBe(true);
  });

  it("detects the native export bridge", () => {
    expect(
      isXYBuddyNativeEmbed({
        search: "",
        userAgent: "Safari",
        nativeBridge: { version: 7 },
      }),
    ).toBe(true);
  });

  it("detects a custom XYBuddyMac user agent", () => {
    expect(
      isXYBuddyNativeEmbed({
        search: "",
        userAgent: "Mozilla/5.0 XYBuddyMac",
      }),
    ).toBe(true);
  });
});
