import type { MidiImportRole } from "./midiImporter";
import { trackStructTemplateFromBytes } from "./image_writer";

export type OpXyPresetCategory =
  | "bass"
  | "bells"
  | "brass"
  | "drum"
  | "fx"
  | "keys"
  | "lead"
  | "organ"
  | "pad"
  | "percussion"
  | "pluck"
  | "strings"
  | "synth"
  | "wind";

export type OpXyPresetChoice = {
  id: string;
  label: string;
  presetPath: string;
  category: OpXyPresetCategory;
  source: "built-in" | "installed";
  templateTrack?: number;
  donorUrl?: string;
  fallbackPresetId?: string;
};

const captured = (
  id: string,
  label: string,
  category: OpXyPresetCategory,
  fallbackPresetId: string,
): OpXyPresetChoice => ({
  id,
  label,
  category,
  presetPath: `${category}/${label}`,
  source: "installed",
  donorUrl: `${import.meta.env.BASE_URL}opxy-presets/${id}.xy`,
  fallbackPresetId,
});

export const OP_XY_PRESET_CHOICES: readonly OpXyPresetChoice[] = [
  {
    id: "drum-boop",
    label: "boop",
    presetPath: "drum/boop",
    category: "drum",
    source: "built-in",
    templateTrack: 1,
  },
  {
    id: "drum-in-phase",
    label: "in phase",
    presetPath: "drum/in phase",
    category: "drum",
    source: "built-in",
    templateTrack: 2,
  },
  {
    id: "bass-shoulder",
    label: "shoulder",
    presetPath: "bass/shoulder",
    category: "bass",
    source: "built-in",
    templateTrack: 3,
  },
  {
    id: "pluck-beach-bum",
    label: "beach bum",
    presetPath: "pluck/beach bum",
    category: "pluck",
    source: "built-in",
    templateTrack: 4,
  },
  {
    id: "lead-gaussian",
    label: "gaussian",
    presetPath: "lead/gaussian",
    category: "lead",
    source: "built-in",
    templateTrack: 5,
  },
  {
    id: "pluck-dielectric",
    label: "dielectric",
    presetPath: "pluck/dielectric",
    category: "pluck",
    source: "built-in",
    templateTrack: 6,
  },
  {
    id: "strings-draemy",
    label: "draemy",
    presetPath: "strings/draemy",
    category: "strings",
    source: "built-in",
    templateTrack: 7,
  },
  {
    id: "pad-bandpasser",
    label: "bandpasser",
    presetPath: "pad/bandpasser",
    category: "pad",
    source: "built-in",
    templateTrack: 8,
  },
  captured("nt-grand-piano", "nt-grand piano", "keys", "pluck-beach-bum"),
  captured("nt-bright-piano", "nt-bright piano", "keys", "pluck-beach-bum"),
  captured("nt-harpsicord", "nt-harpsicord", "pluck", "pluck-dielectric"),
  captured("nt-harpsi", "nt-harpsi", "pluck", "pluck-dielectric"),
  captured("nt-glockenspiel", "nt-glockenspiel", "bells", "pluck-beach-bum"),
  captured("nt-draw-organ", "nt-draw organ", "organ", "pad-bandpasser"),
  captured("nt-dry-lute", "nt-dry lute", "pluck", "pluck-beach-bum"),
  captured("nt-acoustic-bass", "nt-acoustic bass", "bass", "bass-shoulder"),
  captured("nt-cello", "nt-cello", "strings", "strings-draemy"),
  captured(
    "nt-coffee-strings",
    "nt-coffee strings",
    "strings",
    "strings-draemy",
  ),
  captured("nt-broken-timpani", "nt-broken timpani", "percussion", "drum-boop"),
  captured("nt-fat-brass", "nt-fat brass", "brass", "lead-gaussian"),
  captured("nt-accord", "nt-accord", "wind", "lead-gaussian"),
  captured("nt-digital-breath", "nt-digital breath", "wind", "lead-gaussian"),
  captured("nt-broken-lead", "nt-broken lead", "lead", "lead-gaussian"),
  captured("nt-celestial", "nt-celestial", "pad", "pad-bandpasser"),
] as const;

const PRESET_BY_ID = new Map(
  OP_XY_PRESET_CHOICES.map((preset) => [preset.id, preset]),
);

export function opXyPresetById(id: string): OpXyPresetChoice | undefined {
  return PRESET_BY_ID.get(id);
}

function writeLatin1(
  target: Uint8Array,
  offset: number,
  capacity: number,
  value: string,
): void {
  const bytes = new TextEncoder().encode(value);
  if (bytes.length >= capacity) {
    throw new Error(`OP-XY preset path is too long: ${value}`);
  }
  target.fill(0, offset, offset + capacity);
  target.set(bytes, offset);
}

function readLatin1(
  source: Uint8Array,
  offset: number,
  capacity: number,
): string {
  const bytes = source.subarray(offset, offset + capacity);
  const end = bytes.indexOf(0);
  return new TextDecoder("latin1").decode(
    end >= 0 ? bytes.subarray(0, end) : bytes,
  );
}

/**
 * Rehome corpus donors from the capture folder (`1`) to the matching OP-XY
 * library group without altering the fixed-size device struct.
 */
export function opXyTrackStructFromDonor(
  preset: OpXyPresetChoice,
  donorBytes: Uint8Array,
): Uint8Array {
  const trackStruct = trackStructTemplateFromBytes(donorBytes);
  writeLatin1(trackStruct, 0x453f, 48, preset.presetPath);

  const capturedPrefix = `/fat32/presets/1/${preset.label}.preset/`;
  const devicePrefix = `/fat32/presets/${preset.category}/${preset.label}.preset/`;
  for (let region = 0; region < 24; region++) {
    const pathOffset = 0x395f + region * 0x80;
    const path = readLatin1(trackStruct, pathOffset, 72);
    if (path.startsWith(capturedPrefix)) {
      writeLatin1(
        trackStruct,
        pathOffset,
        72,
        devicePrefix + path.slice(capturedPrefix.length),
      );
    }
  }
  return trackStruct;
}

export function recommendedOpXyPresetId(
  programNumber: number,
  role: MidiImportRole,
  isDrum: boolean,
): string {
  if (isDrum) return "drum-boop";
  if (programNumber === 0) return "nt-grand-piano";
  if (programNumber === 1) return "nt-bright-piano";
  if (programNumber === 6) return "nt-harpsicord";
  if (programNumber === 7) return "nt-harpsi";
  if (programNumber <= 7) return "nt-grand-piano";
  if (programNumber <= 15) return "nt-glockenspiel";
  if (programNumber <= 23) return "nt-draw-organ";
  if (programNumber <= 31) return "nt-dry-lute";
  if (programNumber <= 39) return "nt-acoustic-bass";
  if (programNumber <= 47)
    return programNumber === 47 ? "nt-broken-timpani" : "nt-cello";
  if (programNumber <= 55) return "nt-coffee-strings";
  if (programNumber <= 63) return "nt-fat-brass";
  if (programNumber <= 79)
    return programNumber >= 72 ? "nt-digital-breath" : "nt-accord";
  if (programNumber <= 87) return "nt-broken-lead";
  if (programNumber <= 95) return "nt-celestial";
  if (programNumber <= 103) return "lead-gaussian";
  if (programNumber <= 111) return "nt-dry-lute";
  if (programNumber <= 119) return "nt-glockenspiel";
  if (role === "bass") return "bass-shoulder";
  if (role === "chord") return "pad-bandpasser";
  return "lead-gaussian";
}

let donorPromise: Promise<Record<string, Uint8Array>> | null = null;

export function loadOpXyPresetDonors(): Promise<Record<string, Uint8Array>> {
  donorPromise ??= Promise.all(
    OP_XY_PRESET_CHOICES.filter(
      (preset): preset is OpXyPresetChoice & { donorUrl: string } =>
        typeof preset.donorUrl === "string",
    ).map(async (preset) => {
      const response = await fetch(preset.donorUrl);
      if (!response.ok) return null;
      return [preset.id, new Uint8Array(await response.arrayBuffer())] as const;
    }),
  ).then((entries) => {
    const donors: Record<string, Uint8Array> = {};
    for (const entry of entries) {
      if (entry) donors[entry[0]] = entry[1];
    }
    return donors;
  });
  return donorPromise;
}
