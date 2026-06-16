import { writable } from 'svelte/store';
import { ImageProject } from '../lib/xy/image_writer';

export const projectStore = writable<ImageProject | null>(null);
export const activeTrackStore = writable<number>(1);
export const activePatternStore = writable<number>(0); // 0-indexed pattern
