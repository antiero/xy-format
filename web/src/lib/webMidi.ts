import {
  nativeMidiOutputAvailable,
  requestNativeMidiOutputs,
  sendNativeMidi,
  type XYBuddyNativeMidiOutput,
} from "./nativeBridge";

export const XYBUDDY_TESTFLIGHT_URL =
  "https://testflight.apple.com/join/Hg8CwZNE";

export type MidiOutputChoice = XYBuddyNativeMidiOutput;

type BrowserMidiOutput = {
  id: string;
  name?: string | null;
  send(data: number[], timestamp?: number): void;
};

type BrowserMidiAccess = {
  outputs: {
    values(): IterableIterator<BrowserMidiOutput>;
    get(id: string): BrowserMidiOutput | undefined;
  };
};

type NavigatorWithMidi = Navigator & {
  requestMIDIAccess?: (options?: {
    sysex?: boolean;
    software?: boolean;
  }) => Promise<BrowserMidiAccess>;
};

export function isSafariBrowser(userAgent = navigator.userAgent): boolean {
  return (
    /Safari/i.test(userAgent) &&
    !/(Chrome|Chromium|CriOS|Edg|OPR|Firefox|FxiOS)/i.test(userAgent)
  );
}

class WebMidiOutputService {
  private access: BrowserMidiAccess | null = null;
  private selectedOutputId = "";

  public get isNative(): boolean {
    return nativeMidiOutputAvailable();
  }

  async requestOutputs(): Promise<MidiOutputChoice[]> {
    if (this.isNative) return requestNativeMidiOutputs();
    const midiNavigator = navigator as NavigatorWithMidi;
    if (!midiNavigator.requestMIDIAccess) {
      throw new Error(
        isSafariBrowser()
          ? "Safari needs the XYBuddy app for MIDI output."
          : "Web MIDI output is not available in this browser.",
      );
    }
    const access = await midiNavigator.requestMIDIAccess({ sysex: false });
    this.access = access;
    return Array.from(access.outputs.values()).map((output) => ({
      id: output.id,
      name: output.name || "MIDI output",
    }));
  }

  selectOutput(outputId: string): void {
    this.selectedOutputId = outputId;
  }

  preferredOutput(outputs: MidiOutputChoice[]): MidiOutputChoice | undefined {
    return (
      outputs.find((output) => /op[- ]?xy/i.test(output.name)) ?? outputs[0]
    );
  }

  noteOn(trackIndex: number, note: number, velocity: number): void {
    this.send([0x90 | (trackIndex & 0x0f), note & 0x7f, velocity & 0x7f]);
  }

  noteOff(trackIndex: number, note: number, delayMs = 0): void {
    this.send([0x80 | (trackIndex & 0x0f), note & 0x7f, 0], delayMs);
  }

  stopAll(): void {
    for (let channel = 0; channel < 8; channel++) {
      this.send([0xb0 | channel, 123, 0]);
    }
  }

  private send(data: number[], delayMs = 0): void {
    if (!this.selectedOutputId) return;
    if (this.isNative) {
      sendNativeMidi({
        outputId: this.selectedOutputId,
        data,
        delayMs,
      });
      return;
    }
    this.access?.outputs
      .get(this.selectedOutputId)
      ?.send(data, performance.now() + delayMs);
  }
}

export const webMidiOutputService = new WebMidiOutputService();
