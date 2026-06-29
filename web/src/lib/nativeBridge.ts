export type XYBuddyNativeExportPayload = {
  filename: string;
  base64Data: string;
  metadata: {
    sourceMidiFilename: string | null;
    generatorVersion: string;
    xyFormatVersion: string;
  };
  compatibilityStatus: "unknownFirmware";
};

type XYBuddyNativeBridge = {
  version?: number;
  supportsExplicitExports?: boolean;
  pushExport?: (payload: XYBuddyNativeExportPayload) => number;
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
