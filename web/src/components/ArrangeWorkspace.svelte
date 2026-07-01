<script lang="ts">
  import { onDestroy } from "svelte";
  import { audioService } from "../lib/audio";
  import {
    dispatchProjectEdit,
    announceDisplayMessage,
    currentTickStore,
    isPlayingStore,
  } from "../stores/project";
  import { buildArrangerFrame, type ArrangerFrame } from "../lib/xy/arranger";
  import { exportableMidiNoteCount } from "../lib/xy/midiExporter";
  import {
    collectSongPlaybackEvents,
    collectSongPlaybackSteps,
    crossesPlaybackPosition,
    songStepIndexAtPosition,
    type PlaybackEvent,
  } from "../lib/xy/playback";
  import type { XYProjectViewModel } from "../lib/xy/projectViewModel";
  import ArrangeExportActions from "./ArrangeExportActions.svelte";
  import ArrangeTrackColumn from "./ArrangeTrackColumn.svelte";

  export let project: XYProjectViewModel;
  export let onEditMidi: (() => void) | null = null;

  let selectedStepIndex = 0;
  let frame: ArrangerFrame;
  let includeDisabledTracks = false;
  let animationFrame = 0;
  let lastFrameMs = 0;
  let lastPlaybackPosition16ths = 0;
  let activePlaybackStep = -1;
  let transportState: "idle" | "loading" | "playing" = "idle";

  $: frame = buildArrangerFrame(project, selectedStepIndex);
  $: exportOptions = { includeDisabledTracks };
  $: exportableNotes = exportableMidiNoteCount(project, exportOptions);
  $: sequenceName = frame.sequence.source === "song" ? "song 1" : "scenes";
  $: songSteps = collectSongPlaybackSteps(project, frame.sequence.sceneIndexes);
  $: playbackEvents = collectSongPlaybackEvents(project, songSteps, {
    instrumentTrackCount: 8,
  });
  $: songLength16ths = songSteps.reduce(
    (length, step) => length + step.length16ths,
    0,
  );
  function msPer16th(): number {
    return 15000 / Math.max(10, project.tempoBpm || 120);
  }
  function schedulePlaybackEvent(event: PlaybackEvent) {
    const durationMs = Math.max(30, event.duration16ths * msPer16th());
    audioService.noteOn(event.trackIndex, event.note, event.velocity);
    audioService.noteOff(event.trackIndex, event.note, durationMs);
  }
  function syncScene(position16ths: number) {
    const stepIndex = songStepIndexAtPosition(songSteps, position16ths);
    const step = songSteps[stepIndex];
    if (!step || stepIndex === activePlaybackStep) return;
    activePlaybackStep = stepIndex;
    selectedStepIndex = stepIndex;
    dispatchProjectEdit({
      type: "set-active-scene",
      sceneIndex: step.sceneIndex,
    });
  }
  function playbackFrame(now: number) {
    if (!$isPlayingStore || songLength16ths <= 0) return;
    if (!lastFrameMs) lastFrameMs = now;

    const previous = lastPlaybackPosition16ths;
    const next = Math.min(
      songLength16ths,
      previous + (now - lastFrameMs) / msPer16th(),
    );
    lastFrameMs = now;

    for (const event of playbackEvents) {
      if (crossesPlaybackPosition(event.start16ths, previous, next, false)) {
        schedulePlaybackEvent(event);
      }
    }

    lastPlaybackPosition16ths = next;
    currentTickStore.set(next);
    syncScene(next);

    if (next >= songLength16ths) {
      stopPlayback();
      announceDisplayMessage("SONG END", "neutral");
      return;
    }
    animationFrame = requestAnimationFrame(playbackFrame);
  }
  function playEventsAt(position16ths: number) {
    for (const event of playbackEvents) {
      if (Math.abs(event.start16ths - position16ths) < 0.001) {
        schedulePlaybackEvent(event);
      }
    }
  }
  async function togglePlayback() {
    if ($isPlayingStore) {
      stopPlayback();
      announceDisplayMessage("STOP", "neutral");
      return;
    }
    if (songSteps.length === 0 || playbackEvents.length === 0) return;

    transportState = "loading";
    try {
      await audioService.ensureReady();
      const selectedStart = songSteps[frame.selectedStepIndex]?.start16ths ?? 0;
      lastPlaybackPosition16ths =
        $currentTickStore >= songLength16ths
          ? selectedStart
          : $currentTickStore;
      lastFrameMs = performance.now();
      isPlayingStore.set(true);
      transportState = "playing";
      syncScene(lastPlaybackPosition16ths);
      playEventsAt(lastPlaybackPosition16ths);
      animationFrame = requestAnimationFrame(playbackFrame);
      announceDisplayMessage("ARRANGE PLAY", "play");
    } catch {
      transportState = "idle";
      isPlayingStore.set(false);
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
    selectStep(0);
    lastPlaybackPosition16ths = 0;
    currentTickStore.set(0);
    announceDisplayMessage("REWIND", "neutral");
  }
  function selectStep(index: number) {
    const step = frame.sequence.steps[index];
    if (!step) return;
    selectedStepIndex = index;
    dispatchProjectEdit({
      type: "set-active-scene",
      sceneIndex: step.sceneIndex,
    });
  }
  function moveStep(delta: number) {
    selectStep(
      Math.max(
        0,
        Math.min(
          frame.sequence.steps.length - 1,
          frame.selectedStepIndex + delta,
        ),
      ),
    );
  }
  function editMidi() {
    stopPlayback();
    onEditMidi?.();
  }
  onDestroy(() => {
    stopPlayback();
  });
</script>

<section class="arranger-workspace" aria-label="OP-XY Arranger">
  <header class="arranger-topline">
    <div>
      <p>{sequenceName}</p>
      <h2>arrange</h2>
    </div>
    <div class="arranger-status">
      <span title="Current scene">scene {frame.scene.index + 1}</span>
      <span title="Project tempo">{project.tempoBpm.toFixed(1)} bpm</span>
      <span title="Exportable decoded instrument notes">{exportableNotes}</span>
    </div>
  </header>

  <div class="arranger-display">
    <div class="arranger-columns" aria-label="Pattern arrangement">
      {#each frame.columns as column (column.trackIndex)}
        <ArrangeTrackColumn {column} />
      {/each}
    </div>
  </div>

  <footer class="arranger-footer">
    <div class="scene-nav" aria-label="Arrangement scenes">
      <button
        type="button"
        aria-label="Previous scene"
        title="Previous scene"
        disabled={frame.selectedStepIndex === 0}
        on:click={() => moveStep(-1)}>←</button
      >
      <div class="scene-strip">
        {#each frame.sequence.steps as step (step.index)}
          <button
            type="button"
            class:active={step.index === frame.selectedStepIndex}
            aria-label={`${sequenceName} step ${step.index + 1}, scene ${step.sceneIndex + 1}`}
            title={`scene ${step.sceneIndex + 1}`}
            on:click={() => selectStep(step.index)}
          >
            {step.sceneIndex + 1}
          </button>
        {/each}
      </div>
      <button
        type="button"
        aria-label="Next scene"
        title="Next scene"
        disabled={frame.selectedStepIndex >= frame.sequence.steps.length - 1}
        on:click={() => moveStep(1)}>→</button
      >
    </div>

    <ArrangeExportActions
      {project}
      bind:includeDisabledTracks
      {exportableNotes}
      isPlaying={$isPlayingStore}
      {transportState}
      playbackAvailable={playbackEvents.length > 0}
      onTogglePlayback={togglePlayback}
      onRewindPlayback={rewindPlayback}
      onEditMidi={onEditMidi ? editMidi : null}
    />
  </footer>
</section>

<style>
  .arranger-workspace {
    width: min(1120px, 100%);
    margin: 0 auto;
    padding: 26px 18px 34px;
  }

  .arranger-topline,
  .arranger-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
  }

  .arranger-topline {
    margin-bottom: 14px;
  }

  .arranger-topline p,
  .arranger-status span {
    margin: 0;
    color: var(--xy-text-muted);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    text-transform: uppercase;
  }

  .arranger-topline h2 {
    margin: 2px 0 0;
    color: var(--xy-text);
    font-size: 22px;
    font-weight: 520;
    line-height: 1;
    text-transform: uppercase;
  }

  .arranger-status,
  .scene-nav {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .arranger-status {
    justify-content: flex-end;
    flex-wrap: wrap;
  }

  .arranger-status span {
    border: 1px solid #2a2a2d;
    background: #080808;
    padding: 6px 8px;
  }

  .arranger-display {
    position: relative;
    overflow-x: auto;
    overflow-y: hidden;
    border: 1px solid #3a3a40;
    border-radius: 8px;
    background: #000;
    box-shadow: 0 18px 52px rgba(0, 0, 0, 0.38);
    scrollbar-width: none;
  }
  .arranger-display::-webkit-scrollbar {
    width: 0;
    height: 0;
  }
  .arranger-display::before {
    content: "";
    position: absolute;
    z-index: 2;
    left: 0;
    right: 0;
    top: calc((100% - 54px - 54px) / 2);
    height: 54px;
    border-top: 1px solid rgba(255, 255, 255, 0.55);
    border-bottom: 1px solid rgba(255, 255, 255, 0.55);
    pointer-events: none;
  }

  .arranger-columns {
    display: grid;
    grid-template-columns: repeat(8, minmax(92px, 1fr));
    min-width: 736px;
    height: 414px;
  }
  .arranger-footer {
    margin-top: 12px;
    min-width: 0;
  }
  .scene-nav {
    min-width: 0;
    flex: 1;
  }
  .scene-strip {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .scene-strip::-webkit-scrollbar {
    width: 0;
    height: 0;
  }
  .scene-strip button {
    min-width: 34px;
    padding: 0 8px;
    font-variant-numeric: tabular-nums;
  }
  .scene-strip button.active {
    border-color: #f3f1ef;
    background: #f3f1ef;
    color: #050505;
  }
  .arranger-footer button {
    min-height: 32px;
    border-color: #33343a;
    background: #151515;
    color: #efeeec;
    box-shadow: none;
  }
  .arranger-footer button:hover:not(:disabled) {
    border-color: #76777d;
    background: #24242a;
  }
  .arranger-footer button.active {
    border-color: #f3f1ef;
    background: #f3f1ef;
    color: #050505;
  }
  @media (max-width: 760px) {
    .arranger-topline,
    .arranger-footer {
      align-items: flex-start;
      flex-direction: column;
    }

    .arranger-columns {
      grid-template-columns: repeat(8, 72px);
      min-width: 576px;
      height: 374px;
    }
  }
</style>
