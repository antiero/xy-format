import { get, writable } from 'svelte/store';
import { applyEdit, type XYEdit, type XYProjectViewModel } from '../lib/xy/projectViewModel';

export type WorkspaceMode = 'project' | 'pattern' | 'arrange' | 'inspect';
export type SceneClipboard = {
  patternByTrack: number[];
  mutedTracks: boolean[];
} | null;

export const projectStore = writable<XYProjectViewModel | null>(null);
export const activeModeStore = writable<WorkspaceMode>('project');
export const sceneClipboardStore = writable<SceneClipboard>(null);

export const scrollXStore = writable<number>(0);
export const scrollYStore = writable<number>(0);
export const isPlayingStore = writable<boolean>(false);
export const currentTickStore = writable<number>(0);

export function dispatchProjectEdit(edit: XYEdit): void {
  const project = get(projectStore);
  if (!project) return;
  projectStore.set(applyEdit(project, edit));
}
