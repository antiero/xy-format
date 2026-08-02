import { copyFile, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const webDirectory = path.resolve(scriptDirectory, "..");
const repoDirectory = path.resolve(webDirectory, "..");
const sourceDirectory = path.join(
  repoDirectory,
  "src",
  "presets",
  "presetprojs",
);
const outputDirectory = path.join(webDirectory, "public", "opxy-presets");

const presets = {
  "nt-grand-piano": "nt-grand piano.xy",
  "nt-bright-piano": "nt-bright piano.xy",
  "nt-harpsicord": "nt-harpsicord.xy",
  "nt-harpsi": "nt-harpsi.xy",
  "nt-glockenspiel": "nt-glockenspiel.xy",
  "nt-draw-organ": "nt-draw organ.xy",
  "nt-dry-lute": "nt-dry lute.xy",
  "nt-acoustic-bass": "nt-acoustic bass.xy",
  "nt-cello": "nt-cello.xy",
  "nt-coffee-strings": "nt-coffee strings.xy",
  "nt-broken-timpani": "nt-broken timpani.xy",
  "nt-fat-brass": "nt-fat brass.xy",
  "nt-accord": "nt-accord.xy",
  "nt-digital-breath": "nt-digital breath.xy",
  "nt-broken-lead": "nt-broken lead.xy",
  "nt-celestial": "nt-celestial.xy",
};

await mkdir(outputDirectory, { recursive: true });
await Promise.all(
  Object.entries(presets).map(([id, filename]) =>
    copyFile(
      path.join(sourceDirectory, filename),
      path.join(outputDirectory, `${id}.xy`),
    ),
  ),
);
