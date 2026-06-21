import { readFileSync } from "fs";
import { ImageProject } from "../src/lib/xy/image_writer";

const files = [
  "../output/ode_to_joy_v2.xy",
  "../output/mp2_v5_105b_novel_dense.xy",
];

for (const file of files) {
  console.log(`\nTesting ${file}...`);
  const fileBytes = readFileSync(file);
  const proj = ImageProject.fromBytes(new Uint8Array(fileBytes));
  console.log("Track starts found:", proj["starts"].length);
  for (let i = 1; i <= 16; i++) {
    try {
      const notes = proj.getNotes(i);
      if (notes.length > 0) {
        console.log(`Track ${i} notes: ${notes.length}`);
      }
    } catch (e) {
      console.error(`Track ${i} error: ${e.message}`);
    }
  }
}
