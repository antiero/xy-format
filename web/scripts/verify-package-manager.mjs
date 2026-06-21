import { readFileSync } from "node:fs";

const packageJson = JSON.parse(
  readFileSync(new URL("../package.json", import.meta.url), "utf8"),
);

const expected = packageJson.packageManager;
const actual = process.env.npm_config_user_agent
  ?.split(" ")[0]
  ?.replace("/", "@");

if (actual !== expected) {
  console.error(
    `Expected ${expected}, but install is running with ${actual ?? "unknown npm"}.`,
  );
  console.error(`Run: npm install --global ${expected}`);
  process.exit(1);
}
