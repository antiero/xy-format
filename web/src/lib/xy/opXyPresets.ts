import type { MidiImportRole } from "./midiImporter";
import { trackStructTemplateFromBytes } from "./image_writer";

export type OpXyPresetCategory =
  | "bass"
  | "drum"
  | "keys"
  | "lead"
  | "organ"
  | "pad"
  | "pluck"
  | "strings";

export const OP_XY_FACTORY_CATEGORIES: readonly OpXyPresetCategory[] = [
  "bass",
  "drum",
  "keys",
  "lead",
  "organ",
  "pad",
  "pluck",
  "strings",
] as const;

const OP_XY_FACTORY_TRACKS = [
  { role: "Drums", preset: "boop" },
  { role: "Drums / Bass", preset: "in phase" },
  { role: "Bass / Pluck", preset: "shoulder" },
  { role: "Pluck / Lead", preset: "beach bum" },
  { role: "Lead / Soft Pluck", preset: "gaussian" },
  { role: "Soft Pluck / Strings", preset: "dielectric" },
  { role: "Strings / Pad", preset: "draemy" },
  { role: "Pad", preset: "bandpasser" },
] as const;

export function opXyFactoryTrackDescription(trackNumber: number): string {
  const track = OP_XY_FACTORY_TRACKS[trackNumber - 1];
  return track
    ? `OP-XY Track ${trackNumber}: ${track.role} (${track.preset})`
    : `OP-XY Track ${trackNumber}`;
}

export type OpXyPresetChoice = {
  id: string;
  label: string;
  category: OpXyPresetCategory;
  source: "built-in" | "installed";
  templateTrack?: number;
  donorUrl?: string;
  donorTrack?: number;
  fallbackPresetId?: string;
};

const capturedFactoryPreset = (
  id: string,
  label: string,
  category: OpXyPresetCategory,
  donorTrack: number,
  fallbackPresetId: string,
): OpXyPresetChoice => ({
  id,
  label,
  category,
  source: "built-in",
  donorUrl: `${import.meta.env.BASE_URL}opxy-presets/${id}.xy`,
  donorTrack,
  fallbackPresetId,
});

export const OP_XY_PRESET_CHOICES: readonly OpXyPresetChoice[] = [
  {
    id: "drum-boop",
    label: "boop",
    category: "drum",
    source: "built-in",
    templateTrack: 1,
  },
  {
    id: "drum-in-phase",
    label: "in phase",
    category: "drum",
    source: "built-in",
    templateTrack: 2,
  },
  {
    id: "bass-shoulder",
    label: "shoulder",
    category: "bass",
    source: "built-in",
    templateTrack: 3,
  },
  {
    id: "pluck-beach-bum",
    label: "beach bum",
    category: "pluck",
    source: "built-in",
    templateTrack: 4,
  },
  {
    id: "lead-gaussian",
    label: "gaussian",
    category: "lead",
    source: "built-in",
    templateTrack: 5,
  },
  {
    id: "pluck-dielectric",
    label: "dielectric",
    category: "pluck",
    source: "built-in",
    templateTrack: 6,
  },
  {
    id: "strings-draemy",
    label: "draemy",
    category: "strings",
    source: "built-in",
    templateTrack: 7,
  },
  capturedFactoryPreset(
    "strings-ensemble",
    "ensemble",
    "strings",
    8,
    "strings-draemy",
  ),
  capturedFactoryPreset(
    "strings-intimate-str",
    "intimate str",
    "strings",
    8,
    "strings-draemy",
  ),
  capturedFactoryPreset(
    "strings-nachtmusik",
    "nachtmusik",
    "strings",
    8,
    "strings-draemy",
  ),
  capturedFactoryPreset(
    "strings-pointe",
    "pointe",
    "strings",
    8,
    "strings-draemy",
  ),
  capturedFactoryPreset(
    "strings-soutenu",
    "soutenu",
    "strings",
    8,
    "strings-draemy",
  ),
  capturedFactoryPreset(
    "strings-whitness",
    "whitness",
    "strings",
    8,
    "strings-draemy",
  ),
  {
    id: "pad-bandpasser",
    label: "bandpasser",
    category: "pad",
    source: "built-in",
    templateTrack: 8,
  },
] as const;

/**
 * OP-XY factory browser names, transcribed from firmware 1.1.21.
 *
 * A catalogue entry is not automatically safe to author into a project: the
 * `.xy` track stores opaque engine state as well as the displayed preset name.
 * `OP_XY_PRESET_CHOICES` remains the byte-validated subset that has a pristine
 * device-authored track template available to the web importer.
 */
export const OP_XY_FACTORY_PRESET_NAMES = {
  bass: [
    "alloy",
    "any time",
    "bark",
    "belch bass",
    "big square",
    "blank",
    "corduroy",
    "essex",
    "flyby",
    "guitar low",
    "haymaker",
    "iguana",
    "jacket",
    "line check",
    "loney bass",
    "mineral",
    "not fm",
    "off guard",
    "pocket",
    "pressure",
    "rear 424",
    "shark attack",
    "shoulder",
    "sonorous",
    "trunk",
    "under bron",
    "valves",
    "wobbler",
  ],
  drum: [
    "boop",
    "chamine",
    "dead spot",
    "fletcher",
    "in phase",
    "kerf",
    "martini",
    "mushroom",
    "playwood",
    "sugar",
    "wood box",
    "zebra",
  ],
  keys: [
    "80s lover",
    "ambi piano",
    "corporate",
    "dark",
    "drodezzz",
    "elect piano",
    "electric",
    "foal",
    "jeans",
    "key keys",
    "man stage",
    "medieval",
    "missing you",
    "needs tuning",
    "newshour",
    "piano 1",
    "piano 2",
    "refelt piano",
    "shine",
    "slush",
    "spacious",
    "swelvet",
    "tonk 5",
    "vintage",
    "wakeup",
    "whurl xy",
  ],
  lead: [
    "asinine",
    "azimith",
    "beam",
    "bowed",
    "burbie",
    "dustmite",
    "far field",
    "gaussian",
    "gradient",
    "insomniac",
    "low ride",
    "massage",
    "millinery",
    "modulus",
    "open cell",
    "runway",
    "sad triangle",
    "saw 101",
    "sonar",
    "spud mate",
    "swell",
    "top spin",
    "uknowaxel",
    "whirrs",
    "wide saw",
    "wool",
    "wub",
  ],
  organ: [
    "chorale",
    "chunk",
    "dusty org",
    "fm organ",
    "hammy xy3",
    "harmonium",
    "joker",
    "manual",
    "meat org",
    "post order",
    "vestigial",
  ],
  pad: [
    "bandpasser",
    "chambre",
    "chuba",
    "confucius",
    "dark choir",
    "dream choir",
    "frontier",
    "kowalski",
    "murmel",
    "night sky",
    "op1 pad",
    "padawan",
    "qiviut",
    "rich pad",
    "separee",
    "spectre",
    "subsun",
    "there is hope",
    "ulysses",
    "unravel",
    "uranium",
    "zafu",
  ],
  pluck: [
    "avant garde",
    "beach bum",
    "bellissimo",
    "bellonboards",
    "coin",
    "deep luck",
    "dielectric",
    "dingus",
    "endless",
    "guitar",
    "kvarnofon",
    "layered",
    "leftovers",
    "marimba",
    "odorant",
    "on tape",
    "pale crepe",
    "rally",
    "resobubble",
    "rift",
    "soft tines",
    "synth bell",
    "whorl",
  ],
  strings: [
    "draemy",
    "ensemble",
    "intimate str",
    "nachtmusik",
    "pointe",
    "soutenu",
    "whitness",
  ],
} as const satisfies Record<OpXyPresetCategory, readonly string[]>;

const PRESET_BY_ID = new Map(
  OP_XY_PRESET_CHOICES.map((preset) => [preset.id, preset]),
);

export type OpXyFactoryPresetCatalogEntry = {
  id: string;
  label: string;
  category: OpXyPresetCategory;
  available: boolean;
};

function factoryPresetId(category: OpXyPresetCategory, label: string): string {
  const slug = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `${category}-${slug}`;
}

export const OP_XY_FACTORY_PRESET_CATALOG: readonly OpXyFactoryPresetCatalogEntry[] =
  OP_XY_FACTORY_CATEGORIES.flatMap((category) =>
    OP_XY_FACTORY_PRESET_NAMES[category].map((label) => {
      const id = factoryPresetId(category, label);
      return { id, label, category, available: PRESET_BY_ID.has(id) };
    }),
  );

export function opXyPresetById(id: string): OpXyPresetChoice | undefined {
  return PRESET_BY_ID.get(id);
}

/**
 * Extract a captured preset's track state without changing its device paths.
 * Installed sampler assets remain at their device-validated location, such as
 * `/fat32/presets/1/...`; UI categories must never rewrite storage paths.
 */
export function opXyTrackStructFromDonor(donorBytes: Uint8Array): Uint8Array;
export function opXyTrackStructFromDonor(
  preset: OpXyPresetChoice,
  donorBytes: Uint8Array,
): Uint8Array;
export function opXyTrackStructFromDonor(
  presetOrDonorBytes: OpXyPresetChoice | Uint8Array,
  donorBytes?: Uint8Array,
): Uint8Array {
  if (!donorBytes) {
    return trackStructTemplateFromBytes(presetOrDonorBytes as Uint8Array);
  }
  const preset = presetOrDonorBytes as OpXyPresetChoice;
  return trackStructTemplateFromBytes(donorBytes, preset.donorTrack ?? 1);
}

export function recommendedOpXyPresetId(
  programNumber: number,
  role: MidiImportRole,
  isDrum: boolean,
): string {
  if (isDrum) return "drum-boop";
  if (programNumber <= 15) return "pluck-dielectric";
  if (programNumber <= 23) return "pad-bandpasser";
  if (programNumber <= 31) return "pluck-beach-bum";
  if (programNumber <= 39) return "bass-shoulder";
  if (programNumber <= 47)
    return programNumber === 47 ? "drum-boop" : "strings-draemy";
  if (programNumber <= 55) return "strings-draemy";
  if (programNumber <= 87) return "lead-gaussian";
  if (programNumber <= 95) return "pad-bandpasser";
  if (programNumber <= 103) return "lead-gaussian";
  if (programNumber <= 111) return "pluck-beach-bum";
  if (programNumber <= 119) return "pluck-dielectric";
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
