import { readFileSync } from 'fs';
import { ImageProject } from '../src/lib/xy/image_writer';

const fileBytes = readFileSync('../output/mp2_v7_diag_t1both_dense_t3clone.xy');
const image = new Uint8Array(fileBytes);
const proj = ImageProject.fromBytes(image);

for (let i = 1; i <= 16; i++) {
    const pc = proj.getPatternCount(i);
    console.log(`Track ${i}: pattern count = ${pc}`);
    for (let p = 0; p < pc; p++) {
        const notes = proj.getNotes(i, p);
        console.log(`  Pattern ${p+1}: notes = ${notes.length}`);
    }
}
