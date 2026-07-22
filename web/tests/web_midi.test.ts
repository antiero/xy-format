import { afterEach, describe, expect, it, vi } from "vitest";
import { isSafariBrowser, webMidiOutputService } from "../src/lib/webMidi";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("MIDI output preview", () => {
  it("identifies Safari without treating Chromium browsers on Apple devices as Safari", () => {
    expect(
      isSafariBrowser(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/605.1.15 Version/18.5 Safari/605.1.15",
      ),
    ).toBe(true);
    expect(
      isSafariBrowser(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 Chrome/137.0 Safari/537.36",
      ),
    ).toBe(false);
  });

  it("prefers an OP-XY destination and sends tracks on channels 1 to 8", async () => {
    const sent: Array<{ data: number[]; timestamp?: number }> = [];
    const outputs = new Map([
      [
        "iac",
        {
          id: "iac",
          name: "IAC Driver",
          send: vi.fn(),
        },
      ],
      [
        "opxy",
        {
          id: "opxy",
          name: "OP-XY MIDI",
          send: (data: number[], timestamp?: number) =>
            sent.push({ data, timestamp }),
        },
      ],
    ]);
    vi.stubGlobal("window", {});
    vi.stubGlobal("navigator", {
      userAgent: "Chrome",
      requestMIDIAccess: async () => ({ outputs }),
    });

    const choices = await webMidiOutputService.requestOutputs();
    const preferred = webMidiOutputService.preferredOutput(choices);
    expect(preferred?.id).toBe("opxy");
    webMidiOutputService.selectOutput("opxy");
    webMidiOutputService.noteOn(3, 60, 100);
    webMidiOutputService.noteOff(3, 60, 250);

    expect(sent[0].data).toEqual([0x93, 60, 100]);
    expect(sent[1].data).toEqual([0x83, 60, 0]);
    expect((sent[1].timestamp ?? 0) - (sent[0].timestamp ?? 0)).toBeGreaterThan(
      200,
    );
  });
});
