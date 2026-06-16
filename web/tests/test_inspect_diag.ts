import { readFileSync } from 'fs';
import { decodeProject } from '../src/lib/xy/rle';

const fileBytes = readFileSync('../output/mp2_v7_diag_t1both_dense_t3clone.xy');
const { image } = decodeProject(new Uint8Array(fileBytes));

const TRACK_BASE0 = 0x0D79;
const TRACK_COUNT = 16;
const TRACK_STRIDE = 17876;
const OFF_NOTE_COUNT = 0x456F;
const NOTE_SIZE = 12;

let pos = TRACK_BASE0;
for (let i = 0; i < TRACK_COUNT; i++) {
    const patternCount = image[pos];
    console.log(`Track ${i+1}: patternCount at pos ${pos} = ${patternCount}`);
    const noteCount = image[pos + OFF_NOTE_COUNT];
    console.log(`Track ${i+1}: noteCount = ${noteCount}`);

    pos += TRACK_STRIDE + noteCount * NOTE_SIZE;

    for (let p = 1; p < patternCount; p++) {
        const cloneStart = pos - 1;
        const nc = image[cloneStart + OFF_NOTE_COUNT];
        console.log(`  Pattern ${p+1}: cloneStart=${cloneStart}, noteCount=${nc}`);
        pos = cloneStart + TRACK_STRIDE + nc * NOTE_SIZE;
    }
}
