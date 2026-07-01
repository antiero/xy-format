export type ZipEntry = {
  filename: string;
  bytes: Uint8Array;
};

export type ZipProgress = {
  current: number;
  total: number;
  filename: string;
};

const textEncoder = new TextEncoder();
let crcTable: Uint32Array | null = null;

function getCrcTable(): Uint32Array {
  if (crcTable) return crcTable;
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i += 1) {
    let value = i;
    for (let bit = 0; bit < 8; bit += 1) {
      value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
    }
    table[i] = value >>> 0;
  }
  crcTable = table;
  return table;
}

function crc32(bytes: Uint8Array): number {
  const table = getCrcTable();
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc = table[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function writeUint16(view: DataView, offset: number, value: number): void {
  view.setUint16(offset, value, true);
}

function writeUint32(view: DataView, offset: number, value: number): void {
  view.setUint32(offset, value >>> 0, true);
}

function concat(parts: Uint8Array[]): Uint8Array {
  const total = parts.reduce((sum, part) => sum + part.length, 0);
  const output = new Uint8Array(total);
  let offset = 0;
  for (const part of parts) {
    output.set(part, offset);
    offset += part.length;
  }
  return output;
}

function zipDate(): { time: number; date: number } {
  const now = new Date();
  return {
    time:
      (now.getHours() << 11) |
      (now.getMinutes() << 5) |
      Math.floor(now.getSeconds() / 2),
    date:
      ((now.getFullYear() - 1980) << 9) |
      ((now.getMonth() + 1) << 5) |
      now.getDate(),
  };
}

export async function createZipArchive(
  entries: ZipEntry[],
  onProgress?: (progress: ZipProgress) => void,
): Promise<Uint8Array> {
  const parts: Uint8Array[] = [];
  const centralDirectory: Uint8Array[] = [];
  const { time, date } = zipDate();
  let offset = 0;

  for (let index = 0; index < entries.length; index += 1) {
    const entry = entries[index];
    const filename = textEncoder.encode(entry.filename);
    const checksum = crc32(entry.bytes);
    const localHeader = new Uint8Array(30 + filename.length);
    const localView = new DataView(localHeader.buffer);

    writeUint32(localView, 0, 0x04034b50);
    writeUint16(localView, 4, 20);
    writeUint16(localView, 6, 0x0800);
    writeUint16(localView, 8, 0);
    writeUint16(localView, 10, time);
    writeUint16(localView, 12, date);
    writeUint32(localView, 14, checksum);
    writeUint32(localView, 18, entry.bytes.length);
    writeUint32(localView, 22, entry.bytes.length);
    writeUint16(localView, 26, filename.length);
    localHeader.set(filename, 30);

    const centralHeader = new Uint8Array(46 + filename.length);
    const centralView = new DataView(centralHeader.buffer);
    writeUint32(centralView, 0, 0x02014b50);
    writeUint16(centralView, 4, 20);
    writeUint16(centralView, 6, 20);
    writeUint16(centralView, 8, 0x0800);
    writeUint16(centralView, 10, 0);
    writeUint16(centralView, 12, time);
    writeUint16(centralView, 14, date);
    writeUint32(centralView, 16, checksum);
    writeUint32(centralView, 20, entry.bytes.length);
    writeUint32(centralView, 24, entry.bytes.length);
    writeUint16(centralView, 28, filename.length);
    writeUint32(centralView, 42, offset);
    centralHeader.set(filename, 46);

    parts.push(localHeader, entry.bytes);
    centralDirectory.push(centralHeader);
    offset += localHeader.length + entry.bytes.length;
    onProgress?.({
      current: index + 1,
      total: entries.length,
      filename: entry.filename,
    });
    await Promise.resolve();
  }

  const centralStart = offset;
  const centralBytes = concat(centralDirectory);
  const end = new Uint8Array(22);
  const endView = new DataView(end.buffer);
  writeUint32(endView, 0, 0x06054b50);
  writeUint16(endView, 8, entries.length);
  writeUint16(endView, 10, entries.length);
  writeUint32(endView, 12, centralBytes.length);
  writeUint32(endView, 16, centralStart);

  return concat([...parts, centralBytes, end]);
}
