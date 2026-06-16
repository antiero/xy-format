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

    noteOn(channel: number, note: number, velocity: number, delayMs: number = 0) {
        if (!this.synth || !this.context) return;
        const time = this.context.currentTime + delayMs / 1000;
        this.synth.noteOn(channel, note, velocity, { time });
    }

    noteOff(channel: number, note: number, delayMs: number = 0) {
        if (!this.synth || !this.context) return;
        const time = this.context.currentTime + delayMs / 1000;
        this.synth.noteOff(channel, note, { time });
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
