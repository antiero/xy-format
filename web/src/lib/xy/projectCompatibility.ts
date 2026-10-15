import { leaderStartsFromImage, patternStartsFromImage } from "./image_writer";
import { decodeProject } from "./rle";

export type XYProjectCompatibilityStatus =
  | "knownCompatible"
  | "unknownFirmware";

export type XYProjectCompatibilityAssessment = {
  status: XYProjectCompatibilityStatus;
  headerVersion: string;
  rawSha256: string;
  layoutFingerprint: string;
  decodedBytes: number;
  trackCount: number;
  patternCounts: number[];
};

const KNOWN_EDITABLE_HEADER_VERSIONS = new Set(["09130386", "09130686"]);

function hex(bytes: Uint8Array): string {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join(
    "",
  );
}

async function sha256(value: Uint8Array): Promise<string> {
  const source = new Uint8Array(value);
  const digest = await crypto.subtle.digest("SHA-256", source.buffer);
  return hex(new Uint8Array(digest));
}

export async function assessXYProject(
  bytes: Uint8Array,
): Promise<XYProjectCompatibilityAssessment> {
  const { header, image } = decodeProject(bytes);
  const leaders = leaderStartsFromImage(image);
  const patterns = patternStartsFromImage(image);
  if (leaders.length !== 16 || patterns.length !== 16) {
    throw new Error("This OP-XY project layout is not safe to open.");
  }

  const headerVersion = hex(header.slice(4));
  const patternCounts = patterns.map((track) => track.length);
  const layoutDescription = JSON.stringify({
    decodedBytes: image.length,
    leaders,
    patternCounts,
  });
  const layoutFingerprint = await sha256(
    new TextEncoder().encode(layoutDescription),
  );

  return {
    status: KNOWN_EDITABLE_HEADER_VERSIONS.has(headerVersion)
      ? "knownCompatible"
      : "unknownFirmware",
    headerVersion,
    rawSha256: await sha256(bytes),
    layoutFingerprint,
    decodedBytes: image.length,
    trackCount: leaders.length,
    patternCounts,
  };
}
