import { describe, expect, it } from "vitest";
import { decode, RleError } from "../src/lib/xy/rle";

describe("RLE safety limits", () => {
  it("rejects decoded output over the configured limit", () => {
    expect(() =>
      decode(new Uint8Array([0, 0, 255]), 0, undefined, 256),
    ).toThrow(RleError);
  });
});
