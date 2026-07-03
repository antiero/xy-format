<script lang="ts">
  import { onDestroy } from "svelte";
  import {
    announceDisplayMessage,
    currentTickStore,
    dispatchProjectEdit,
    editHistoryStore,
    isPlayingStore,
    redoProjectEdit,
    scrollXStore,
    scrollYStore,
    undoProjectEdit,
  } from "../stores/project";
  import ProjectTempoControl from "./ProjectTempoControl.svelte";
  import { audioService } from "../lib/audio";
  import { STEP_TICKS } from "../lib/xy/image_writer";
  import {
    collectPlaybackEvents,
    crossesPlaybackPosition,
    playbackLoopLength16ths,
    type PlaybackEvent,
    type PlaybackScope,
  } from "../lib/xy/playback";
  import { display16thsAsBars, scaleTo16thsPerStep } from "../lib/xy/timing";
  import {
    projectTracksWithStepData,
    type XYNoteViewModel,
    type XYPatternViewModel,
    type XYProjectViewModel,
  } from "../lib/xy/projectViewModel";

  export let project: XYProjectViewModel;

  const KEY_COLUMN_WIDTH = 58;
  const ROW_HEIGHT = 22;
  const NOTE_HEIGHT = 18;
  const MIN_DURATION_16THS = 1 / 16;
  const MAX_PATTERN_NOTES = 120;

  type NoteClipboardItem = {
    startOffset16ths: number;
    duration16ths: number;
    note: number;
    velocity: number;
    flags0: number;
    flags1: number;
  };

  type NoteClipboard = {
    width16ths: number;
    notes: NoteClipboardItem[];
  };

  type DragMode = "move" | "resize-start" | "resize-end";

  type DragStartNote = Pick<
    XYNoteViewModel,
    | "id"
    | "tick"
    | "gateTicks"
    | "note"
    | "velocity"
    | "start16ths"
    | "duration16ths"
  >;

  type NoteDraft = {
    tick: number;
    gateTicks: number;
    note: number;
    start16ths: number;
    duration16ths: number;
  };

  let timelineMode: "fit" | "global" = "fit";
  let playbackScope: PlaybackScope = "track";
  let pxPer16th = 34;
  let gridEl: HTMLDivElement;
  let animationFrame = 0;
  let lastFrameMs = 0;
  let lastPlaybackPosition16ths = 0;
  let transportState: "idle" | "loading" | "playing" = "idle";
  let playbackError = "";
  let selectedNoteIds: string[] = [];
  let selectionContext = "";
  let noteClipboard: NoteClipboard | null = null;
  let dragState: {
    mode: DragMode;
    startClientX: number;
    startClientY: number;
    notes: DragStartNote[];
  } | null = null;
  let dragDrafts: Record<string, NoteDraft> = {};
  let dragMoved = false;

  $: track = project.tracks[project.activeTrackIndex];
  $: pattern = track.patterns[project.activePatternIndex] ?? track.patterns[0];
  $: selectionContextKey = `${track.index}:${pattern.index}`;
  $: if (selectionContext !== selectionContextKey) {
    selectionContext = selectionContextKey;
    selectedNoteIds = project.selectedNoteId ? [project.selectedNoteId] : [];
    dragState = null;
    dragDrafts = {};
  }
  $: {
    const validNoteIds = new Set(pattern.notes.map((note) => note.id));
    const validSelectedNoteIds = selectedNoteIds.filter((id) =>
      validNoteIds.has(id),
    );
    if (validSelectedNoteIds.length !== selectedNoteIds.length) {
      selectedNoteIds = validSelectedNoteIds;
    }
  }
  $: selectedNotes = pattern.notes.filter((note) =>
    selectedNoteIds.includes(note.id),
  );
  $: selectedNote = selectedNotes[0];
  $: selectedCount = selectedNotes.length;
  $: selectedSummary =
    selectedCount === 0
      ? "none"
      : selectedCount === 1
        ? (selectedNote?.noteName ?? "one note")
        : `${selectedCount} notes`;
  $: tracksWithStepData = projectTracksWithStepData(project);
  $: visibleTrackPads =
    tracksWithStepData.length === 0
      ? project.tracks
      : tracksWithStepData.some((candidate) => candidate.index === track.index)
        ? tracksWithStepData
        : [...tracksWithStepData, track].sort((a, b) => a.index - b.index);
  $: visibleNotes = makeVisibleNotes(pattern);
  $: playbackEvents = collectPlaybackEvents(
    project,
    playbackScope,
    track.index,
    pattern.index,
    project.activeSceneIndex,
  );
  $: loopLength16ths = playbackLoopLength16ths(
    project,
    playbackScope,
    track.index,
    pattern.index,
    project.activeSceneIndex,
  );
  $: timelineLength =
    timelineMode === "global"
      ? Math.max(
          ...project.tracks.flatMap((candidate) =>
            candidate.patterns.map((p) => p.effectiveLength16ths),
          ),
          pattern.effectiveLength16ths,
          loopLength16ths,
        )
      : Math.max(pattern.effectiveLength16ths, loopLength16ths);
  $: rollWidth = Math.max(720, timelineLength * pxPer16th);
  $: scaleFactor = scaleTo16thsPerStep(pattern.trackScale) ?? 1;
  $: playbackProgress =
    loopLength16ths > 0 ? Math.min(1, $currentTickStore / loopLength16ths) : 0;
  $: playheadLeft =
    KEY_COLUMN_WIDTH + Math.min(timelineLength, $currentTickStore) * pxPer16th;

  function makeVisibleNotes(current: XYPatternViewModel): number[] {
    if (current.notes.length === 0) {
      return Array.from({ length: 49 }, (_, i) => 84 - i);
    }
    const pitches = current.notes.map((note) => note.note);
    const max = Math.min(108, Math.max(...pitches) + 5);
    const min = Math.max(24, Math.min(...pitches) - 5);
    return Array.from({ length: max - min + 1 }, (_, i) => max - i);
  }

  function noteName(note: number): string {
    const names = [
      "C",
      "C#",
      "D",
      "D#",
      "E",
      "F",
      "F#",
      "G",
      "G#",
      "A",
      "A#",
      "B",
    ];
    return `${names[note % 12]}${Math.floor(note / 12) - 1}`;
  }

  function clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value));
  }

  function uniqueIds(ids: string[]): string[] {
    return [...new Set(ids)];
  }

  function isNoteSelected(noteId: string): boolean {
    return selectedNoteIds.includes(noteId);
  }

  function setSelectedNotes(noteIds: string[], primaryId = noteIds[0]) {
    selectedNoteIds = uniqueIds(noteIds);
    dispatchProjectEdit({ type: "select-note", noteId: primaryId });
  }

  function clearSelectedNotes() {
    selectedNoteIds = [];
    dispatchProjectEdit({ type: "select-note", noteId: undefined });
  }

  function selectNoteById(noteId: string) {
    setSelectedNotes([noteId], noteId);
  }

  function nextSelectionForGesture(
    event: MouseEvent | PointerEvent,
    noteId: string,
  ): string[] {
    if (event.shiftKey || event.metaKey || event.ctrlKey) {
      return selectedNoteIds.includes(noteId)
        ? selectedNoteIds.filter((id) => id !== noteId)
        : [...selectedNoteIds, noteId];
    }
    return selectedNoteIds.includes(noteId) ? selectedNoteIds : [noteId];
  }

  function selectedNotesForEdit(): XYNoteViewModel[] {
    return pattern.notes.filter((note) => selectedNoteIds.includes(note.id));
  }

  function patternEnd16ths(): number {
    return Math.max(MIN_DURATION_16THS, pattern.effectiveLength16ths);
  }

  function start16thsToTick(start16ths: number): number {
    return Math.max(0, Math.round((start16ths / scaleFactor) * STEP_TICKS));
  }

  function duration16thsToGate(duration16ths: number): number {
    return Math.max(
      1,
      Math.round(
        (Math.max(MIN_DURATION_16THS, duration16ths) / scaleFactor) *
          STEP_TICKS,
      ),
    );
  }

  function noteDraft(
    note: DragStartNote,
    start16ths: number,
    duration16ths: number,
    pitch: number,
  ): NoteDraft {
    const tick = start16thsToTick(start16ths);
    const gateTicks = duration16thsToGate(duration16ths);
    return {
      tick,
      gateTicks,
      note: pitch,
      start16ths,
      duration16ths: Math.max(MIN_DURATION_16THS, duration16ths),
    };
  }

  function draftChanged(note: DragStartNote, draft: NoteDraft): boolean {
    return (
      draft.tick !== note.tick ||
      draft.gateTicks !== note.gateTicks ||
      draft.note !== note.note
    );
  }

  function renderNote(note: XYNoteViewModel): NoteDraft {
    return (
      dragDrafts[note.id] ?? {
        tick: note.tick,
        gateTicks: note.gateTicks,
        note: note.note,
        start16ths: note.start16ths,
        duration16ths: note.duration16ths,
      }
    );
  }

  function noteAtStep(step: number): XYNoteViewModel | undefined {
    return pattern.notes.find((note) => note.displayStep === step);
  }

  function selectTrack(trackIndex: number) {
    stopPlayback();
    dispatchProjectEdit({ type: "set-active-track", trackIndex });
  }

  function selectPattern(patternIndex: number) {
    stopPlayback();
    dispatchProjectEdit({ type: "set-active-pattern", patternIndex });
  }

  function setSteps(steps: number) {
    dispatchProjectEdit({
      type: "set-pattern-steps",
      trackIndex: track.index,
      patternIndex: pattern.index,
      steps,
    });
  }

  function setScale(scale: string) {
    dispatchProjectEdit({
      type: "set-track-scale",
      trackIndex: track.index,
      patternIndex: pattern.index,
      scale: scale as never,
    });
  }

  function handleGridClick(event: MouseEvent) {
    if (!gridEl) return;
    const rect = gridEl.getBoundingClientRect();
    const x = event.clientX - rect.left + gridEl.scrollLeft - KEY_COLUMN_WIDTH;
    const y = event.clientY - rect.top + gridEl.scrollTop;
    if (x < 0) return;
    const start16ths = Math.max(0, x / pxPer16th);
    const tick = Math.floor(start16ths / scaleFactor) * STEP_TICKS;
    const row = Math.floor(y / ROW_HEIGHT);
    const pitch = visibleNotes[row];
    if (pitch === undefined || tick >= pattern.totalSteps * STEP_TICKS) return;

    dispatchProjectEdit({
      type: "add-note",
      trackIndex: track.index,
      patternIndex: pattern.index,
      note: {
        tick,
        gateTicks: STEP_TICKS,
        note: pitch,
        velocity: 100,
      },
    });
    selectedNoteIds = [];
    announceDisplayMessage("NOTE ADDED", "ok");
    void previewMidiNote(track.index, pitch, 100, STEP_TICKS);
  }

  function handleGridKeydown(event: KeyboardEvent) {
    const key = event.key.toLowerCase();
    if (key === "escape") {
      clearSelectedNotes();
      return;
    }
    if (key === "delete" || key === "backspace") {
      event.preventDefault();
      deleteSelectedNotes();
      return;
    }
    if ((event.metaKey || event.ctrlKey) && key === "a") {
      event.preventDefault();
      setSelectedNotes(
        pattern.notes.map((note) => note.id),
        pattern.notes[0]?.id,
      );
      announceDisplayMessage(`SELECTED ${pattern.notes.length} NOTES`);
      return;
    }
    if ((event.metaKey || event.ctrlKey) && key === "c") {
      event.preventDefault();
      copySelectedNotes();
      return;
    }
    if ((event.metaKey || event.ctrlKey) && key === "x") {
      event.preventDefault();
      cutSelectedNotes();
      return;
    }
    if ((event.metaKey || event.ctrlKey) && key === "v") {
      event.preventDefault();
      pasteNotes();
    }
  }

  function selectNote(event: MouseEvent, note: XYNoteViewModel) {
    event.stopPropagation();
    const nextSelection = nextSelectionForGesture(event, note.id);
    setSelectedNotes(nextSelection, note.id);
    void previewMidiNote(
      track.index,
      note.note,
      note.velocity,
      Math.min(note.gateTicks, STEP_TICKS * 2),
    );
  }

  function updateSelected(patch: Partial<XYNoteViewModel>) {
    if (!selectedNote) return;
    dispatchProjectEdit({
      type: "update-note",
      trackIndex: track.index,
      patternIndex: pattern.index,
      noteId: selectedNote.id,
      patch,
    });
  }

  function deleteSelectedNotes(message = "DELETED") {
    const notes = selectedNotesForEdit();
    if (notes.length === 0) return;
    dispatchProjectEdit({
      type: "delete-notes",
      trackIndex: track.index,
      patternIndex: pattern.index,
      noteIds: notes.map((note) => note.id),
    });
    selectedNoteIds = [];
    announceDisplayMessage(
      `${message} ${notes.length} NOTE${notes.length === 1 ? "" : "S"}`,
    );
  }

  function copySelectedNotes(): boolean {
    const notes = selectedNotesForEdit();
    if (notes.length === 0) return false;
    const minStart = Math.min(...notes.map((note) => note.start16ths));
    const maxEnd = Math.max(
      ...notes.map((note) => note.start16ths + note.duration16ths),
    );
    noteClipboard = {
      width16ths: Math.max(MIN_DURATION_16THS, maxEnd - minStart),
      notes: notes.map((note) => ({
        startOffset16ths: note.start16ths - minStart,
        duration16ths: note.duration16ths,
        note: note.note,
        velocity: note.velocity,
        flags0: note.flags0,
        flags1: note.flags1,
      })),
    };
    announceDisplayMessage(
      `COPIED ${notes.length} NOTE${notes.length === 1 ? "" : "S"}`,
    );
    return true;
  }

  function cutSelectedNotes() {
    if (copySelectedNotes()) {
      deleteSelectedNotes("CUT");
    }
  }

  function pasteNotes() {
    if (!noteClipboard || noteClipboard.notes.length === 0) return;
    const remaining = MAX_PATTERN_NOTES - pattern.notes.length;
    if (remaining <= 0) {
      announceDisplayMessage("NOTE LIMIT", "warn");
      return;
    }

    const sourceNotes = noteClipboard.notes.slice(0, remaining);
    const selectedStart =
      selectedNotes.length > 0
        ? Math.min(...selectedNotes.map((note) => note.start16ths)) + 1
        : 0;
    const targetStart = clamp(
      $currentTickStore > 0 ? Math.round($currentTickStore) : selectedStart,
      0,
      Math.max(0, patternEnd16ths() - noteClipboard.width16ths),
    );
    const notes = sourceNotes.map((item) => {
      const start16ths = clamp(
        targetStart + item.startOffset16ths,
        0,
        Math.max(0, patternEnd16ths() - MIN_DURATION_16THS),
      );
      const duration16ths = Math.min(
        item.duration16ths,
        Math.max(MIN_DURATION_16THS, patternEnd16ths() - start16ths),
      );
      return {
        tick: start16thsToTick(start16ths),
        gateTicks: duration16thsToGate(duration16ths),
        note: clamp(item.note, 0, 127),
        velocity: item.velocity,
        flags0: item.flags0,
        flags1: item.flags1,
      };
    });

    dispatchProjectEdit({
      type: "add-notes",
      trackIndex: track.index,
      patternIndex: pattern.index,
      notes,
    });
    selectedNoteIds = [];
    announceDisplayMessage(
      `PASTED ${notes.length} NOTE${notes.length === 1 ? "" : "S"}`,
      "ok",
    );
  }

  function beginNoteDrag(
    event: PointerEvent,
    note: XYNoteViewModel,
    mode: DragMode,
  ) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();

    const nextSelection = nextSelectionForGesture(event, note.id);
    setSelectedNotes(nextSelection, note.id);
    if (!nextSelection.includes(note.id)) return;

    const notes = pattern.notes.filter((candidate) =>
      nextSelection.includes(candidate.id),
    );
    dragState = {
      mode,
      startClientX: event.clientX,
      startClientY: event.clientY,
      notes: notes.map((candidate) => ({
        id: candidate.id,
        tick: candidate.tick,
        gateTicks: candidate.gateTicks,
        note: candidate.note,
        velocity: candidate.velocity,
        start16ths: candidate.start16ths,
        duration16ths: candidate.duration16ths,
      })),
    };
    dragDrafts = {};
    dragMoved = false;
    window.addEventListener("pointermove", handleNotePointerMove);
    window.addEventListener("pointerup", handleNotePointerUp);
  }

  function handleNotePointerMove(event: PointerEvent) {
    if (!dragState) return;
    event.preventDefault();

    const delta16ths = Math.round(
      (event.clientX - dragState.startClientX) / pxPer16th,
    );
    const deltaRows = Math.round(
      (event.clientY - dragState.startClientY) / ROW_HEIGHT,
    );
    const minVisiblePitch = Math.min(...visibleNotes);
    const maxVisiblePitch = Math.max(...visibleNotes);
    const nextDrafts: Record<string, NoteDraft> = {};

    for (const note of dragState.notes) {
      let start16ths = note.start16ths;
      let duration16ths = note.duration16ths;
      let pitch = note.note;
      const end16ths = note.start16ths + note.duration16ths;

      if (dragState.mode === "move") {
        start16ths = clamp(
          note.start16ths + delta16ths,
          0,
          Math.max(0, patternEnd16ths() - MIN_DURATION_16THS),
        );
        pitch = clamp(note.note - deltaRows, minVisiblePitch, maxVisiblePitch);
      } else if (dragState.mode === "resize-start") {
        start16ths = clamp(
          note.start16ths + delta16ths,
          0,
          Math.max(0, end16ths - MIN_DURATION_16THS),
        );
        duration16ths = Math.max(MIN_DURATION_16THS, end16ths - start16ths);
      } else {
        const nextEnd = clamp(
          end16ths + delta16ths,
          note.start16ths + MIN_DURATION_16THS,
          patternEnd16ths(),
        );
        duration16ths = Math.max(MIN_DURATION_16THS, nextEnd - note.start16ths);
      }

      const draft = noteDraft(note, start16ths, duration16ths, pitch);
      if (draftChanged(note, draft)) {
        nextDrafts[note.id] = draft;
      }
    }

    dragDrafts = nextDrafts;
    dragMoved = Object.keys(nextDrafts).length > 0;
  }

  function cleanupNotePointerDrag() {
    window.removeEventListener("pointermove", handleNotePointerMove);
    window.removeEventListener("pointerup", handleNotePointerUp);
  }

  function handleNotePointerUp(event: PointerEvent) {
    if (!dragState) return;
    event.preventDefault();
    cleanupNotePointerDrag();

    const patches = Object.entries(dragDrafts).map(([noteId, draft]) => ({
      noteId,
      patch: {
        tick: draft.tick,
        gateTicks: draft.gateTicks,
        note: draft.note,
      },
    }));
    const mode = dragState.mode;
    const previewNote = dragState.notes[0];
    dragState = null;
    dragDrafts = {};

    if (dragMoved && patches.length > 0) {
      dispatchProjectEdit({
        type: "update-notes",
        trackIndex: track.index,
        patternIndex: pattern.index,
        patches,
      });
      announceDisplayMessage(
        `${mode === "move" ? "MOVED" : "RESIZED"} ${patches.length} NOTE${patches.length === 1 ? "" : "S"}`,
        "ok",
      );
    } else if (previewNote) {
      void previewMidiNote(
        track.index,
        previewNote.note,
        previewNote.velocity,
        Math.min(previewNote.gateTicks, STEP_TICKS * 2),
      );
    }
    dragMoved = false;
  }

  function handleScroll(event: Event) {
    const target = event.target as HTMLDivElement;
    scrollXStore.set(target.scrollLeft);
    scrollYStore.set(target.scrollTop);
  }

  function msPer16th(): number {
    return 15000 / Math.max(10, project.tempoBpm || 120);
  }

  async function previewMidiNote(
    trackIndex: number,
    note: number,
    velocity = 100,
    gateTicks = STEP_TICKS,
  ) {
    playbackError = "";
    try {
      await audioService.ensureReady();
      const factor = scaleTo16thsPerStep(pattern.trackScale) ?? 1;
      const durationMs = Math.max(
        60,
        (gateTicks / STEP_TICKS) * factor * msPer16th(),
      );
      audioService.noteOn(trackIndex, note, velocity);
      audioService.noteOff(trackIndex, note, durationMs);
    } catch (error) {
      playbackError =
        error instanceof Error ? error.message : "audio unavailable";
    }
  }

  function schedulePlaybackEvent(event: PlaybackEvent) {
    const durationMs = Math.max(30, event.duration16ths * msPer16th());
    audioService.noteOn(event.trackIndex, event.note, event.velocity);
    audioService.noteOff(event.trackIndex, event.note, durationMs);
  }

  function playbackFrame(now: number) {
    if (!$isPlayingStore || loopLength16ths <= 0) return;
    if (!lastFrameMs) lastFrameMs = now;

    const delta16ths = (now - lastFrameMs) / msPer16th();
    lastFrameMs = now;

    const previous = lastPlaybackPosition16ths;
    let next = previous + delta16ths;
    const didWrap = next >= loopLength16ths;
    if (didWrap) {
      next %= loopLength16ths;
      audioService.stopAll();
    }

    for (const event of playbackEvents) {
      if (crossesPlaybackPosition(event.start16ths, previous, next, didWrap)) {
        schedulePlaybackEvent(event);
      }
    }

    lastPlaybackPosition16ths = next;
    currentTickStore.set(next);
    animationFrame = requestAnimationFrame(playbackFrame);
  }

  async function togglePlayback() {
    if ($isPlayingStore) {
      stopPlayback();
      announceDisplayMessage("STOP", "neutral");
      return;
    }

    playbackError = "";
    transportState = "loading";
    try {
      await audioService.ensureReady();
      lastPlaybackPosition16ths =
        $currentTickStore >= loopLength16ths ? 0 : $currentTickStore;
      lastFrameMs = performance.now();
      isPlayingStore.set(true);
      transportState = "playing";
      animationFrame = requestAnimationFrame(playbackFrame);
      announceDisplayMessage(
        `${track.label} P${pattern.index + 1} PLAY`,
        "play",
      );
    } catch (error) {
      transportState = "idle";
      isPlayingStore.set(false);
      playbackError =
        error instanceof Error ? error.message : "audio unavailable";
      announceDisplayMessage("AUDIO UNAVAILABLE", "error");
    }
  }

  function stopPlayback() {
    if (animationFrame) {
      cancelAnimationFrame(animationFrame);
      animationFrame = 0;
    }
    audioService.stopAll();
    isPlayingStore.set(false);
    transportState = "idle";
    lastFrameMs = 0;
  }

  function rewindPlayback() {
    stopPlayback();
    lastPlaybackPosition16ths = 0;
    currentTickStore.set(0);
    announceDisplayMessage("REWIND");
  }

  function setPlaybackScope(scope: PlaybackScope) {
    playbackScope = scope;
    rewindPlayback();
  }

  onDestroy(() => {
    cleanupNotePointerDrag();
    stopPlayback();
  });
</script>

<section class="workspace pattern-workspace">
  <div class="workspace-head">
    <div>
      <p class="eyebrow">Pattern</p>
      <h2>{track.label} · P{pattern.index + 1}</h2>
    </div>
    <div class="status-strip">
      <span>{pattern.totalSteps} steps</span>
      <span>scale {pattern.trackScaleLabel}</span>
      <span>{display16thsAsBars(pattern.effectiveLength16ths)}</span>
    </div>
  </div>

  <div class="editor-layout">
    <aside class="side-rail">
      <div class="rail-section">
        <span class="rail-label">tracks</span>
        <div class="track-pad-grid">
          {#each visibleTrackPads as candidate}
            <button
              class="pad-button"
              class:active={candidate.index === track.index}
              class:red={candidate.colorRole === "red"}
              type="button"
              on:click={() => selectTrack(candidate.index)}
            >
              {candidate.label}
            </button>
          {/each}
        </div>
      </div>

      <div class="rail-section">
        <span class="rail-label">patterns</span>
        <div class="pattern-pad-grid">
          {#each track.patterns as candidate}
            <button
              class="pad-button"
              class:active={candidate.index === pattern.index}
              type="button"
              on:click={() => selectPattern(candidate.index)}
            >
              P{candidate.index + 1}
            </button>
          {/each}
        </div>
      </div>

      <div class="rail-section">
        <span class="rail-label">length</span>
        <label class="field-label">
          steps
          <input
            type="number"
            min="1"
            max="64"
            value={pattern.totalSteps}
            on:change={(event) =>
              setSteps(Number((event.target as HTMLInputElement).value))}
          />
        </label>
        <div class="quick-row">
          {#each [16, 32, 48, 64] as steps}
            <button
              type="button"
              class:active={pattern.totalSteps === steps}
              on:click={() => setSteps(steps)}>{steps / 16}b</button
            >
          {/each}
        </div>
      </div>

      <div class="rail-section">
        <span class="rail-label">scale</span>
        <div class="scale-grid">
          {#each ["1/2", "1", "2", "3", "4", "6", "8", "16"] as scale}
            <button
              type="button"
              class:active={pattern.trackScale === scale}
              disabled={!["1/2", "1", "2", "16"].includes(scale)}
              title={["1/2", "1", "2", "16"].includes(scale)
                ? `set scale ${scale}`
                : `scale ${scale} is read-only until device write tests exist`}
              on:click={() => setScale(scale)}
            >
              {scale}
            </button>
          {/each}
        </div>
      </div>
    </aside>

    <div class="pattern-main">
      <div class="step-panel">
        <div class="section-title">
          <span>OP-XY step view</span>
          <span
            >{pattern.bars} bar{pattern.bars === 1 ? "" : "s"} · final {pattern.finalBarSteps}</span
          >
        </div>
        <div
          class="bar-pages"
          style={`grid-template-columns: repeat(${pattern.bars}, minmax(170px, 1fr));`}
        >
          {#each Array(pattern.bars) as _, barIndex}
            <div
              class="bar-page"
              class:partial={barIndex === pattern.bars - 1 &&
                pattern.finalBarSteps < 16}
            >
              <span class="bar-label">bar {barIndex + 1}</span>
              <div class="step-leds">
                {#each Array(16) as _, stepInBar}
                  {@const step = barIndex * 16 + stepInBar}
                  {@const active = step < pattern.totalSteps}
                  {@const note = noteAtStep(step)}
                  <button
                    type="button"
                    class="step-led"
                    class:on={Boolean(note)}
                    class:inactive={!active}
                    class:selected={note && isNoteSelected(note.id)}
                    disabled={!active}
                    on:click={() => note && selectNoteById(note.id)}
                  >
                    {stepInBar + 1}
                  </button>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      </div>

      <div class="transport-panel">
        <div class="transport-controls">
          <button
            type="button"
            class="transport-play"
            class:active={$isPlayingStore}
            disabled={transportState === "loading" ||
              playbackEvents.length === 0}
            on:click={togglePlayback}
          >
            {$isPlayingStore
              ? "stop"
              : transportState === "loading"
                ? "load"
                : "play"}
          </button>
          <button type="button" on:click={rewindPlayback}>rew</button>
          <div class="segmented tight">
            <button
              type="button"
              class:active={playbackScope === "track"}
              on:click={() => setPlaybackScope("track")}>track</button
            >
            <button
              type="button"
              class:active={playbackScope === "scene"}
              on:click={() => setPlaybackScope("scene")}>scene</button
            >
          </div>
        </div>
        <div class="transport-readout">
          <ProjectTempoControl tempoBpm={project.tempoBpm} />
          <span
            >{playbackEvents.length} note{playbackEvents.length === 1
              ? ""
              : "s"}</span
          >
          <span>{display16thsAsBars(loopLength16ths)}</span>
        </div>
        <div class="transport-meter" aria-hidden="true">
          <span style={`width: ${playbackProgress * 100}%;`}></span>
        </div>
        {#if playbackError}
          <span class="transport-error">{playbackError}</span>
        {/if}
      </div>

      <div class="roll-toolbar">
        <div class="segmented">
          <button
            type="button"
            class:active={timelineMode === "fit"}
            on:click={() => (timelineMode = "fit")}>fit pattern</button
          >
          <button
            type="button"
            class:active={timelineMode === "global"}
            on:click={() => (timelineMode = "global")}>global time</button
          >
        </div>
        <div class="roll-edit-actions">
          <button
            type="button"
            on:click={undoProjectEdit}
            disabled={!$editHistoryStore.canUndo}>undo</button
          >
          <button
            type="button"
            on:click={redoProjectEdit}
            disabled={!$editHistoryStore.canRedo}>redo</button
          >
          <button
            type="button"
            on:click={copySelectedNotes}
            disabled={selectedCount === 0}>copy</button
          >
          <button
            type="button"
            on:click={cutSelectedNotes}
            disabled={selectedCount === 0}>cut</button
          >
          <button type="button" on:click={pasteNotes} disabled={!noteClipboard}
            >paste</button
          >
          <button
            type="button"
            on:click={() => deleteSelectedNotes()}
            disabled={selectedCount === 0}>delete</button
          >
        </div>
        <label class="inline-range">
          zoom
          <input
            type="range"
            min="18"
            max="72"
            step="2"
            bind:value={pxPer16th}
          />
        </label>
      </div>

      <div class="piano-roll" bind:this={gridEl} on:scroll={handleScroll}>
        <div
          class="roll-canvas"
          style={`width: ${rollWidth + KEY_COLUMN_WIDTH}px; height: ${visibleNotes.length * ROW_HEIGHT}px;`}
          role="grid"
          tabindex="0"
          aria-label="Piano roll note grid"
          on:click={handleGridClick}
          on:keydown={handleGridKeydown}
        >
          <div class="key-column">
            {#each visibleNotes as midi}
              <div class="key-label">{noteName(midi)}</div>
            {/each}
          </div>
          <div
            class="roll-grid"
            style={`left: ${KEY_COLUMN_WIDTH}px; width: ${rollWidth}px; height: ${visibleNotes.length * ROW_HEIGHT}px; background-size: ${pxPer16th * 4}px ${ROW_HEIGHT}px, ${pxPer16th}px ${ROW_HEIGHT}px;`}
          ></div>
          {#each Array(Math.ceil(timelineLength / 16)) as _, bar}
            <div
              class="bar-marker"
              style={`left: ${KEY_COLUMN_WIDTH + bar * 16 * pxPer16th}px;`}
            >
              B{bar + 1}
            </div>
          {/each}
          <div
            class="playhead"
            class:active={$isPlayingStore || $currentTickStore > 0}
            style={`left: ${playheadLeft}px; height: ${visibleNotes.length * ROW_HEIGHT}px;`}
          ></div>
          {#each pattern.notes as note}
            {@const rendered = renderNote(note)}
            {@const row = visibleNotes.indexOf(rendered.note)}
            {#if row >= 0}
              <button
                class="roll-note"
                class:selected={isNoteSelected(note.id)}
                class:dragging={Boolean(dragDrafts[note.id])}
                style={`left: ${KEY_COLUMN_WIDTH + rendered.start16ths * pxPer16th}px; top: ${row * ROW_HEIGHT + 2}px; width: ${Math.max(10, rendered.duration16ths * pxPer16th - 2)}px; height: ${NOTE_HEIGHT}px;`}
                type="button"
                aria-label={`${noteName(rendered.note)} at step ${Math.floor(rendered.tick / STEP_TICKS) + 1}`}
                title={`${noteName(rendered.note)} · step ${Math.floor(rendered.tick / STEP_TICKS) + 1}`}
                on:pointerdown={(event) => beginNoteDrag(event, note, "move")}
                on:click|stopPropagation={(event) =>
                  event.detail === 0 && selectNote(event, note)}
              >
                <i
                  class="roll-note-handle handle-start"
                  aria-hidden="true"
                  on:pointerdown|stopPropagation={(event) =>
                    beginNoteDrag(event, note, "resize-start")}
                ></i>
                <span
                  style={`height: ${Math.max(0, 100 - (note.velocity / 127) * 100)}%;`}
                ></span>
                <i
                  class="roll-note-handle handle-end"
                  aria-hidden="true"
                  on:pointerdown|stopPropagation={(event) =>
                    beginNoteDrag(event, note, "resize-end")}
                ></i>
              </button>
            {/if}
          {/each}
        </div>
      </div>
    </div>

    <aside class="inspector">
      <div class="section-title">
        <span>note</span>
        <span>{selectedSummary}</span>
      </div>
      {#if selectedNote}
        <label class="field-label">
          pitch
          <input
            type="number"
            min="0"
            max="127"
            value={selectedNote.note}
            on:change={(event) =>
              updateSelected({
                note: Number((event.target as HTMLInputElement).value),
              })}
          />
        </label>
        <label class="field-label">
          step
          <input
            type="number"
            min="1"
            max={pattern.totalSteps}
            value={selectedNote.displayStep + 1}
            on:change={(event) =>
              updateSelected({
                tick:
                  (Number((event.target as HTMLInputElement).value) - 1) *
                  STEP_TICKS,
              })}
          />
        </label>
        <label class="field-label">
          gate
          <input
            type="number"
            min="1"
            max="64"
            step="0.25"
            value={selectedNote.gateTicks / STEP_TICKS}
            on:change={(event) =>
              updateSelected({
                gateTicks:
                  Number((event.target as HTMLInputElement).value) * STEP_TICKS,
              })}
          />
        </label>
        <label class="field-label">
          velocity
          <input
            type="number"
            min="1"
            max="127"
            value={selectedNote.velocity}
            on:change={(event) =>
              updateSelected({
                velocity: Number((event.target as HTMLInputElement).value),
              })}
          />
        </label>
        <button
          class="secondary-button"
          type="button"
          on:click={() =>
            previewMidiNote(
              track.index,
              selectedNote.note,
              selectedNote.velocity,
              selectedNote.gateTicks,
            )}>audition</button
        >
        <button
          class="danger-button"
          type="button"
          on:click={() => deleteSelectedNotes()}>delete selected</button
        >
      {:else}
        <p class="empty-line">
          Click the roll to add a note, or select existing notes.
        </p>
      {/if}
    </aside>
  </div>
</section>
