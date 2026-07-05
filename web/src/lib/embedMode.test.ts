import { describe, expect, it } from "vitest";
import { isAppleClient, isXYBuddyNativeEmbed } from "./embedMode";

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

describe("isAppleClient", () => {
  it("detects macOS browsers", () => {
    expect(
      isAppleClient({
        userAgent:
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
      }),
    ).toBe(true);
  });

  it("detects iPhone, iPad, and visionOS browsers", () => {
    expect(
      isAppleClient({
        userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X)",
      }),
    ).toBe(true);
    expect(
      isAppleClient({
        userAgent: "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X)",
      }),
    ).toBe(true);
    expect(
      isAppleClient({
        userAgent: "Mozilla/5.0 (Apple Vision; CPU visionOS 2_0 like Mac OS X)",
      }),
    ).toBe(true);
  });

  it("detects iPadOS desktop-mode Safari", () => {
    expect(
      isAppleClient({
        userAgent:
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
        platform: "MacIntel",
        maxTouchPoints: 5,
      }),
    ).toBe(true);
  });

  it("does not detect Windows or Android browsers", () => {
    expect(
      isAppleClient({
        userAgent:
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        platform: "Win32",
      }),
    ).toBe(false);
    expect(
      isAppleClient({
        userAgent:
          "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36",
        platform: "Linux armv8l",
      }),
    ).toBe(false);
  });
});
