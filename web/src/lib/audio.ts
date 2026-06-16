import { WorkletSynthesizer } from 'spessasynth_lib';
import { get } from 'svelte/store';

class AudioService {
    private context: AudioContext | null = null;
    private synth: WorkletSynthesizer | null = null;
    private isReady: boolean = false;
    private initializationPromise: Promise<void> | null = null;

    async init() {
        if (this.isReady) return;
        if (this.initializationPromise) return this.initializationPromise;

        this.initializationPromise = (async () => {
            this.context = new (window.AudioContext || (window as any).webkitAudioContext)();

            // Resume context if suspended (browser autoplay policy)
            if (this.context.state === 'suspended') {
                await this.context.resume();
            }

            // Load worklet processor
            await this.context.audioWorklet.addModule('/spessasynth_processor.min.js');

            this.synth = new WorkletSynthesizer(this.context);
            this.synth.connect(this.context.destination);

            // Fetch default soundfont
            const response = await fetch('/soundfont/A320U.sf2');
            const arrayBuffer = await response.arrayBuffer();

            await this.synth.soundBankManager.addSoundBank(arrayBuffer, 'main');
            await this.synth.isReady;

            this.isReady = true;
        })();

        return this.initializationPromise;
    }

    async ensureReady() {
        if (!this.isReady) {
            await this.init();
        }
        if (this.context?.state === 'suspended') {
            await this.context.resume();
        }
    }

    // General MIDI percussion map for exported drum patterns on channel 10.
    // Maps OP-XY note values to GM Drum map based on PocketOperations.
    private gmDrumNoteMap(note: number): number {
        // Mapped from OP-XY PocketOperations MIDI_NOTE_MAP to GM_DRUM_NOTE_MAP
        const opXyDrumMap: Record<number, number> = {
            53: 36, // BD (Bass Drum)
            56: 38, // SN (Snare) / CB (Cowbell, but OP-XY maps both to 56, we'll map to Snare)
            61: 42, // CH (Closed Hat)
            63: 46, // OH (Open Hat)
            62: 39, // CL (Clap) / HC (Hand Clap) -> actually HC in link is 70? Oh wait:
            // "BD: 53, SN: 56, CH: 61, OH: 63, CL: 62, RS: 57, HT: 69, MT: 67, LT: 65, CY: 49, CB: 56, SH: 60, HC: 70"
            // "BD: 36, SN: 38, CH: 42, OH: 46, CL: 39, RS: 37, HT: 50, MT: 47, LT: 45, CY: 49, CB: 56, SH: 70, HC: 39"
            57: 37, // RS (Rim Shot)
            69: 50, // HT (High Tom)
            67: 47, // MT (Mid Tom)
            65: 45, // LT (Low Tom)
            49: 49, // CY (Cymbal)
            60: 70, // SH (Shaker mapped to Maracas)
            70: 39, // HC (Hand Clap mapped to Hand Clap)
        };
        return opXyDrumMap[note] || note;
    }

    noteOn(channel: number, note: number, velocity: number, delayMs: number = 0) {
        if (!this.synth || !this.context) return;

        // Use channel 9 (10th channel) for drum tracks 0 and 1
        const isDrum = channel === 0 || channel === 1;
        const outChannel = isDrum ? 9 : channel;
        const outNote = isDrum ? this.gmDrumNoteMap(note) : note;

        const time = this.context.currentTime + delayMs / 1000;
        this.synth.noteOn(outChannel, outNote, velocity, { time });
    }

    noteOff(channel: number, note: number, delayMs: number = 0) {
        if (!this.synth || !this.context) return;

        const isDrum = channel === 0 || channel === 1;
        const outChannel = isDrum ? 9 : channel;
        const outNote = isDrum ? this.gmDrumNoteMap(note) : note;

        const time = this.context.currentTime + delayMs / 1000;
        this.synth.noteOff(outChannel, outNote, { time });
    }

    stopAll() {
        if (!this.synth) return;
        for (let ch = 0; ch < 16; ch++) {
           for (let n = 0; n < 128; n++) {
              this.synth.noteOff(ch, n);
           }
        }
    }
}

export const audioService = new AudioService();
