import { readFileSync, readdirSync } from 'fs';
import { ImageProject } from './web/src/lib/xy/image_writer';

const dir = './src/one-off-changes-from-default';
const files = readdirSync(dir).filter(f => f.endsWith('.xy'));

let failed = 0;
for (const file of files) {
  try {
    const fileBytes = readFileSync(`${dir}/${file}`);
    const proj = ImageProject.fromBytes(new Uint8Array(fileBytes));
    for (let i = 1; i <= 16; i++) {
        proj.getNotes(i);
    }
  } catch(e) {
    console.error(`${file}: Error - ${e.message}`);
    failed++;
  }
}
console.log(`Failed getNotes: ${failed} / ${files.length}`);
