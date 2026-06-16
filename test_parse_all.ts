import { readFileSync, readdirSync } from 'fs';
import { ImageProject } from './web/src/lib/xy/image_writer';

const dir = './src/one-off-changes-from-default';
const files = readdirSync(dir).filter(f => f.endsWith('.xy'));

let failed = 0;
for (const file of files) {
  try {
    const fileBytes = readFileSync(`${dir}/${file}`);
    const proj = ImageProject.fromBytes(new Uint8Array(fileBytes));
    if (proj['starts'].length !== 16) {
        console.error(`${file}: found ${proj['starts'].length} starts`);
        failed++;
    }
  } catch(e) {
    console.error(`${file}: Error - ${e.message}`);
    failed++;
  }
}
console.log(`Failed: ${failed} / ${files.length}`);
