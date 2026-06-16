import { writable } from 'svelte/store';
import { ImageProject } from '../lib/xy/image_writer';

export const projectStore = writable<ImageProject | null>(null);
export const activeTrackStore = writable<number>(1);
