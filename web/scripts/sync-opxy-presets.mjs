import { copyFile, mkdir, rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const webDirectory = path.resolve(scriptDirectory, "..");
const repoDirectory = path.resolve(webDirectory, "..");
const sourceDirectory = path.join(
  repoDirectory,
  "src",
  "factory-preset-captures",
  "firmware-1.1.21",
  "strings",
);
const outputDirectory = path.join(webDirectory, "public", "opxy-presets");

const presets = {
  "strings-ensemble": "ensemble.xy",
  "strings-intimate-str": "intimate str.xy",
  "strings-nachtmusik": "nachtmusik.xy",
  "strings-pointe": "pointe.xy",
  "strings-soutenu": "soutenu.xy",
  "strings-whitness": "whitness.xy",
};

await rm(outputDirectory, { recursive: true, force: true });
await mkdir(outputDirectory, { recursive: true });
await Promise.all(
  Object.entries(presets).map(([id, filename]) =>
    copyFile(
      path.join(sourceDirectory, filename),
      path.join(outputDirectory, `${id}.xy`),
    ),
  ),
);
