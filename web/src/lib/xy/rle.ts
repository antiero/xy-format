/**
 * Byte-level RLE codec for the `.xy` container (decoded 2026-06-09).
 */

export const HEADER_LEN = 8;
export const MAGIC = new Uint8Array([0xdd, 0xcc, 0xbb, 0xaa]);
export const MAX_RUN = 257; // 2 literal bytes + extension 255

export class RleError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RleError';
  }
}

export function decode(buf: Uint8Array, start: number = 0, end?: number): Uint8Array {
  const out: number[] = [];
  let i = start;
  const stop = end === undefined ? buf.length : end;
  let prev = -1;

  while (i < stop) {
    const b = buf[i];
    i++;
    out.push(b);

    if (b === prev) {
      if (i >= stop) {
        throw new RleError(`extension byte needed past end at ${i}`);
      }
      const ext = buf[i];
      i++;
      for (let j = 0; j < ext; j++) {
        out.push(b);
      }
      prev = -1;
    } else {
      prev = b;
    }
  }

  return new Uint8Array(out);
}

export function encode(data: Uint8Array): Uint8Array {
  const out: number[] = [];
  let i = 0;
  const n = data.length;

  while (i < n) {
    const v = data[i];
    let j = i;
    while (j < n && data[j] === v) {
      j++;
    }
    let k = j - i;
    while (k >= 2) {
      const c = Math.min(k, MAX_RUN);
      out.push(v);
      out.push(v);
      out.push(c - 2);
      k -= c;
    }
    if (k > 0) {
      out.push(v);
    }
    i = j;
  }

  return new Uint8Array(out);
}

export function decodeProject(data: Uint8Array): { header: Uint8Array; image: Uint8Array } {
  if (data.length < HEADER_LEN) {
    throw new RleError('not a .xy file (too short)');
  }
  for (let i = 0; i < 4; i++) {
    if (data[i] !== MAGIC[i]) {
      throw new RleError('not a .xy file (bad magic)');
    }
  }
  return {
    header: data.slice(0, HEADER_LEN),
    image: decode(data, HEADER_LEN),
  };
}

export function encodeProject(header: Uint8Array, image: Uint8Array): Uint8Array {
  if (header.length !== HEADER_LEN) {
    throw new RleError('header must be exactly 8 bytes');
  }
  for (let i = 0; i < 4; i++) {
    if (header[i] !== MAGIC[i]) {
      throw new RleError('header must have the original 4-byte magic');
    }
  }
  const encodedImage = encode(image);
  const result = new Uint8Array(header.length + encodedImage.length);
  result.set(header);
  result.set(encodedImage, header.length);
  return result;
}
