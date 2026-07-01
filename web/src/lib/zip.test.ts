import { describe, expect, it } from "vitest";
import { createZipArchive } from "./zip";

function readUint32(bytes: Uint8Array, offset: number): number {
  return new DataView(
    bytes.buffer,
    bytes.byteOffset,
    bytes.byteLength,
  ).getUint32(offset, true);
}

describe("createZipArchive", () => {
  it("creates a zip with stored entries and progress callbacks", async () => {
    const progress: string[] = [];
    const zip = await createZipArchive(
      [
        { filename: "demo-trk1.mid", bytes: new Uint8Array([1, 2, 3]) },
        { filename: "demo-trk2.mid", bytes: new Uint8Array([4, 5]) },
      ],
      ({ current, total, filename }) => {
        progress.push(`${current}/${total}:${filename}`);
      },
    );
    const text = new TextDecoder().decode(zip);

    expect(readUint32(zip, 0)).toBe(0x04034b50);
    expect(text).toContain("demo-trk1.mid");
    expect(text).toContain("demo-trk2.mid");
    expect(readUint32(zip, zip.length - 22)).toBe(0x06054b50);
    expect(progress).toEqual(["1/2:demo-trk1.mid", "2/2:demo-trk2.mid"]);
  });
});
