export const GLOBAL_SCENE_LENGTH = 0x08;
export const GLOBAL_TIME_SIGNATURE = 0x1c;

export const SCENE_LENGTH_NAMES = {
  0x00: "longest",
  0x01: "shortest",
  0x02: "time-signature",
} as const;

export const TIME_SIGNATURE_NAMES = {
  0x10: "3/4",
  0x11: "4/4",
  0x12: "5/4",
  0x13: "6/8",
  0x14: "7/8",
  0x15: "12/8",
} as const;

export type SceneLengthModeRaw = keyof typeof SCENE_LENGTH_NAMES;
export type ProjectTimeSignatureRaw = keyof typeof TIME_SIGNATURE_NAMES;
export type ProjectTimeSignature =
  (typeof TIME_SIGNATURE_NAMES)[ProjectTimeSignatureRaw];

export function sceneLengthName(raw: number): string {
  return raw in SCENE_LENGTH_NAMES
    ? SCENE_LENGTH_NAMES[raw as SceneLengthModeRaw]
    : `unknown-0x${raw.toString(16).toUpperCase().padStart(2, "0")}`;
}

export function timeSignatureName(raw: number): string {
  return raw in TIME_SIGNATURE_NAMES
    ? TIME_SIGNATURE_NAMES[raw as ProjectTimeSignatureRaw]
    : `unknown-0x${raw.toString(16).toUpperCase().padStart(2, "0")}`;
}

export function projectTimeSignatureRaw(
  numerator: number,
  denominator: number,
): ProjectTimeSignatureRaw | null {
  const signature = `${numerator}/${denominator}`;
  const entry = Object.entries(TIME_SIGNATURE_NAMES).find(
    ([, name]) => name === signature,
  );
  return entry ? (Number(entry[0]) as ProjectTimeSignatureRaw) : null;
}
