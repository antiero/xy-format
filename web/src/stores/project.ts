import { get, writable } from "svelte/store";
import { ImageProject } from "../lib/xy/image_writer";
import {
  applyEdit,
  buildProjectViewModel,
  type XYEdit,
  type XYProjectViewModel,
} from "../lib/xy/projectViewModel";

export type WorkspaceMode =
  | "project"
  | "daw"
  | "pattern"
  | "arrange"
  | "inspect";
export type SceneClipboard = {
  patternByTrack: number[];
  mutedTracks: boolean[];
} | null;
export type DisplayTone =
  | "neutral"
  | "ok"
  | "warn"
  | "error"
  | "record"
  | "play";
export type DisplayMessage = {
  text: string;
  tone?: DisplayTone;
  ttlMs?: number;
};
export type EditHistoryState = {
  undoDepth: number;
  redoDepth: number;
  canUndo: boolean;
  canRedo: boolean;
};

type ProjectSnapshot = {
  fileName: string;
  modified: boolean;
  activeTrackIndex: number;
  activePatternIndex: number;
  activeSceneIndex: number;
  selectedNoteId?: string;
  header: Uint8Array;
  image: Uint8Array;
};

const projectWritable = writable<XYProjectViewModel | null>(null);

export const projectStore = {
  subscribe: projectWritable.subscribe,
  set(project: XYProjectViewModel | null): void {
    resetProjectHistory();
    projectWritable.set(project);
  },
  update(
    updater: (value: XYProjectViewModel | null) => XYProjectViewModel | null,
  ): void {
    resetProjectHistory();
    projectWritable.update(updater);
  },
};
export const activeModeStore = writable<WorkspaceMode>("project");
export const sceneClipboardStore = writable<SceneClipboard>(null);
export const displayMessageStore = writable<DisplayMessage | null>(null);
export const editHistoryStore = writable<EditHistoryState>({
  undoDepth: 0,
  redoDepth: 0,
  canUndo: false,
  canRedo: false,
});

export const scrollXStore = writable<number>(0);
export const scrollYStore = writable<number>(0);
export const isPlayingStore = writable<boolean>(false);
export const currentTickStore = writable<number>(0);

let displayMessageTimer: ReturnType<typeof setTimeout> | undefined;
let displayMessageId = 0;
const MAX_HISTORY = 80;
let undoStack: ProjectSnapshot[] = [];
let redoStack: ProjectSnapshot[] = [];

function updateHistoryStore(): void {
  editHistoryStore.set({
    undoDepth: undoStack.length,
    redoDepth: redoStack.length,
    canUndo: undoStack.length > 0,
    canRedo: redoStack.length > 0,
  });
}

function resetProjectHistory(): void {
  undoStack = [];
  redoStack = [];
  updateHistoryStore();
}

function snapshotProject(project: XYProjectViewModel): ProjectSnapshot {
  return {
    fileName: project.fileName,
    modified: project.modified,
    activeTrackIndex: project.activeTrackIndex,
    activePatternIndex: project.activePatternIndex,
    activeSceneIndex: project.activeSceneIndex,
    selectedNoteId: project.selectedNoteId,
    header: new Uint8Array(project.imageProject.header),
    image: new Uint8Array(project.imageProject.image),
  };
}

function restoreProject(snapshot: ProjectSnapshot): XYProjectViewModel {
  return buildProjectViewModel(
    new ImageProject(
      new Uint8Array(snapshot.header),
      new Uint8Array(snapshot.image),
    ),
    snapshot.fileName,
    {
      activeTrackIndex: snapshot.activeTrackIndex,
      activePatternIndex: snapshot.activePatternIndex,
      activeSceneIndex: snapshot.activeSceneIndex,
      selectedNoteId: snapshot.selectedNoteId,
    },
    snapshot.modified,
  );
}

function currentSelection(project: XYProjectViewModel) {
  return {
    activeTrackIndex: project.activeTrackIndex,
    activePatternIndex: project.activePatternIndex,
    activeSceneIndex: project.activeSceneIndex,
    selectedNoteId: project.selectedNoteId,
  };
}

export function setProjectFileName(fileName: string): void {
  const project = get(projectWritable);
  if (!project || project.fileName === fileName) return;

  projectWritable.set(
    buildProjectViewModel(
      project.imageProject,
      fileName,
      currentSelection(project),
      project.modified,
    ),
  );
}

function editCreatesHistory(edit: XYEdit): boolean {
  switch (edit.type) {
    case "set-active-track":
    case "set-active-pattern":
    case "set-active-scene":
    case "select-note":
      return false;
    default:
      return true;
  }
}

export function announceDisplayMessage(
  message: string | DisplayMessage,
  tone: DisplayTone = "neutral",
): void {
  const payload =
    typeof message === "string" ? { text: message, tone } : message;
  const id = ++displayMessageId;
  const ttlMs = payload.ttlMs ?? 2600;

  if (displayMessageTimer) {
    clearTimeout(displayMessageTimer);
    displayMessageTimer = undefined;
  }

  displayMessageStore.set({
    text: payload.text,
    tone: payload.tone ?? tone,
    ttlMs,
  });

  if (ttlMs > 0) {
    displayMessageTimer = setTimeout(() => {
      if (displayMessageId === id) {
        displayMessageStore.set(null);
      }
    }, ttlMs);
  }
}

export function dispatchProjectEdit(edit: XYEdit): void {
  const project = get(projectWritable);
  if (!project) return;
  const before = editCreatesHistory(edit) ? snapshotProject(project) : null;
  const next = applyEdit(project, edit);

  if (before) {
    undoStack.push(before);
    if (undoStack.length > MAX_HISTORY) {
      undoStack.shift();
    }
    redoStack = [];
    updateHistoryStore();
  }

  projectWritable.set(next);
}

export function undoProjectEdit(): void {
  const current = get(projectWritable);
  const previous = undoStack.pop();
  if (!current || !previous) return;

  redoStack.push(snapshotProject(current));
  projectWritable.set(restoreProject(previous));
  updateHistoryStore();
  announceDisplayMessage("UNDO", "neutral");
}

export function redoProjectEdit(): void {
  const current = get(projectWritable);
  const next = redoStack.pop();
  if (!current || !next) return;

  undoStack.push(snapshotProject(current));
  projectWritable.set(restoreProject(next));
  updateHistoryStore();
  announceDisplayMessage("REDO", "neutral");
}
