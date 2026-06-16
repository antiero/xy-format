import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'fs';
import { ImageProject } from '../src/lib/xy/image_writer';

describe('.xy parsing', () => {
    it('correctly parses step position and gate length for test files', () => {
        const files = readdirSync('../output').filter(f => f.match(/^\d{2}_pt/)).sort();

        for (const file of files) {
            const fileBytes = readFileSync(`../output/${file}`);
            const proj = ImageProject.fromBytes(new Uint8Array(fileBytes));
            const notes = proj.getNotes(3);

            expect(notes).toHaveLength(1);
            const note = notes[0];

            // Parse filename to get expected step and gate
            // e.g. 01_pt_s01_g01.xy -> step 1, gate 1
            const match = file.match(/_s(\d+)_g(\d+)/);
            expect(match).not.toBeNull();

            if (match) {
                const stepStr = match[1];
                const gateStr = match[2];

                const step = parseInt(stepStr, 10);
                const gateSteps = parseInt(gateStr, 10);

                const expectedTick = (step - 1) * 480;

                // G01 = 240 ticks (half step) based on the test files.
                // G02 = 540
                // G04 = 1920
                // G08 = 3840
                let expectedGate = 0;
                if (gateSteps === 1) expectedGate = 240;
                else if (gateSteps === 2) expectedGate = 540;
                else if (gateSteps === 4) expectedGate = 1920;
                else if (gateSteps === 8) expectedGate = 3840;

                expect(note.tick, `File ${file} tick mismatch`).toBe(expectedTick);
                expect(note.gate, `File ${file} gate mismatch`).toBe(expectedGate);
            }
        }
    });
});
