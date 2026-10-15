import { copyFile, mkdir, readFile, rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const webDirectory = path.resolve(scriptDirectory, "..");
const repoDirectory = path.resolve(webDirectory, "..");
const captureDirectory = path.join(
  repoDirectory,
  "src",
  "factory-preset-captures",
);
const outputDirectory = path.join(webDirectory, "public", "opxy-presets");
const manifestPath = path.join(
  webDirectory,
  "src",
  "lib",
  "xy",
  "opXyFactoryPresetCaptureManifest.json",
);
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));

await rm(outputDirectory, { recursive: true, force: true });
await mkdir(outputDirectory, { recursive: true });
await Promise.all(
  manifest.files.map(({ source, asset, firmware = manifest.firmware }) =>
    copyFile(
      path.join(captureDirectory, `firmware-${firmware}`, source),
      path.join(outputDirectory, asset),
    ),
  ),
);
