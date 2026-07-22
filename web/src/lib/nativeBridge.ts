export type XYBuddyNativeExportPayload = {
  filename: string;
  base64Data: string;
  metadata: {
    sourceMidiFilename: string | null;
    maxPatternsPerTrack?: number;
    generatorVersion: string;
    xyFormatVersion: string;
  };
  compatibilityStatus: "unknownFirmware";
};

export type XYBuddyNativeMidiOutput = {
  id: string;
  name: string;
};

export type XYBuddyNativeMidiMessage = {
  outputId: string;
  data: number[];
  delayMs?: number;
};

type XYBuddyNativeBridge = {
  version?: number;
  supportsExplicitExports?: boolean;
  supportsNativeMidiOutput?: boolean;
  nativeMidiOutputs?: XYBuddyNativeMidiOutput[];
  pushExport?: (payload: XYBuddyNativeExportPayload) => number;
  requestNativeMidiOutputs?: () => number;
  sendNativeMidi?: (message: XYBuddyNativeMidiMessage) => number;
};

declare global {
  interface Window {
    __xyBuddyNativeBridge?: XYBuddyNativeBridge;
  }
}

export function bytesToBase64(bytes: Uint8Array): string {
  const chunkSize = 0x8000;
  let binary = "";
  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode.apply(
      null,
      Array.from(bytes.subarray(index, index + chunkSize)),
    );
  }
  return btoa(binary);
}

export function publishNativeExport(
  payload: XYBuddyNativeExportPayload,
): boolean {
  const bridge = window.__xyBuddyNativeBridge;
  if (typeof bridge?.pushExport !== "function") {
    return false;
  }

  bridge.pushExport(payload);
  window.dispatchEvent(
    new CustomEvent("xybuddy-export-ready", { detail: payload }),
  );
  return true;
}

export function nativeMidiOutputAvailable(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(
    window.__xyBuddyNativeBridge?.supportsNativeMidiOutput &&
    window.__xyBuddyNativeBridge?.sendNativeMidi,
  );
}

export async function requestNativeMidiOutputs(): Promise<
  XYBuddyNativeMidiOutput[]
> {
  const bridge = window.__xyBuddyNativeBridge;
  if (!bridge?.requestNativeMidiOutputs) return [];
  bridge.requestNativeMidiOutputs();
  const current = bridge.nativeMidiOutputs ?? [];
  if (current.length > 0) return current;

  return new Promise((resolve) => {
    const finish = () => {
      window.clearTimeout(timeout);
      window.removeEventListener("xybuddy-midi-outputs", finish);
      resolve(window.__xyBuddyNativeBridge?.nativeMidiOutputs ?? []);
    };
    const timeout = window.setTimeout(finish, 1200);
    window.addEventListener("xybuddy-midi-outputs", finish, { once: true });
  });
}

export function sendNativeMidi(message: XYBuddyNativeMidiMessage): boolean {
  const bridge = window.__xyBuddyNativeBridge;
  if (!bridge?.sendNativeMidi) return false;
  bridge.sendNativeMidi(message);
  return true;
}
