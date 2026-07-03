<script lang="ts">
  import { onDestroy } from "svelte";
  import { audioService } from "../lib/audio";
  import {
    collectSongPlaybackEvents,
    collectSongPlaybackSteps,
    crossesPlaybackPosition,
    songStepIndexAtPosition,
    type PlaybackEvent,
  } from "../lib/xy/playback";
  import {
    announceDisplayMessage,
    currentTickStore,
    dispatchProjectEdit,
    isPlayingStore,
  } from "../stores/project";
  import { buildArrangerSequence } from "../lib/xy/arranger";
  import type { XYProjectViewModel } from "../lib/xy/projectViewModel";
  import ProjectTempoControl from "./ProjectTempoControl.svelte";

  export let project: XYProjectViewModel;
  export let onTempoChange: (tempoBpm: number) => void = () => {};

  const STEPS_PER_PAGE = 32;

  let animationFrame = 0;
  let lastFrameMs = 0;
  let lastPlaybackPosition16ths = 0;
  let selectedSongStep = 0;
  let activePlaybackStep = -1;
  let page = 0;
  let transportState: "idle" | "loading" | "playing" = "idle";
  let playbackError = "";

  $: song = project.songs[0];
  $: sequence = buildArrangerSequence(project);
  $: songSteps = collectSongPlaybackSteps(project, sequence.sceneIndexes);
  $: songEvents = collectSongPlaybackEvents(project, songSteps);
  $: songLength16ths = songSteps.reduce(
    (length, step) => length + step.length16ths,
    0,
  );
  $: selectedSongStep = Math.min(
    Math.max(0, selectedSongStep),
    Math.max(0, songSteps.length - 1),
  );
  $: currentSongStep = songStepIndexAtPosition(songSteps, $currentTickStore);
  $: totalPages = Math.max(1, Math.ceil(songSteps.length / STEPS_PER_PAGE));
  $: page = Math.min(page, totalPages - 1);
  $: pageStart = page * STEPS_PER_PAGE;
  $: gridSlots = Array.from({ length: STEPS_PER_PAGE }, (_, index) => {
    const songStepIndex = pageStart + index;
    return songSteps[songStepIndex]
      ? { songStepIndex, step: songSteps[songStepIndex] }
      : null;
  });

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
    selectedSongStep = stepIndex;
    page = Math.floor(stepIndex / STEPS_PER_PAGE);
    dispatchProjectEdit({
      type: "set-active-scene",
      sceneIndex: step.sceneIndex,
    });
  }

  function playbackFrame(now: number) {
    if (!$isPlayingStore || songLength16ths <= 0) return;
    if (!lastFrameMs) lastFrameMs = now;

    const previous = lastPlaybackPosition16ths;
    let next = previous + (now - lastFrameMs) / msPer16th();
    lastFrameMs = now;
    let didWrap = false;

    if (next >= songLength16ths) {
      if (!song?.loop) {
        currentTickStore.set(songLength16ths);
        selectedSongStep = Math.max(0, songSteps.length - 1);
        stopPlayback();
        announceDisplayMessage("SONG END", "neutral");
        return;
      }
      next %= songLength16ths;
      didWrap = true;
      audioService.stopAll();
    }

    for (const event of songEvents) {
      if (crossesPlaybackPosition(event.start16ths, previous, next, didWrap)) {
        schedulePlaybackEvent(event);
      }
    }

    lastPlaybackPosition16ths = next;
    currentTickStore.set(next);
    syncScene(next);
    animationFrame = requestAnimationFrame(playbackFrame);
  }

  function playEventsAt(position16ths: number) {
    for (const event of songEvents) {
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
    if (songSteps.length === 0 || songEvents.length === 0) return;

    playbackError = "";
    transportState = "loading";
    try {
      await audioService.ensureReady();
      const selectedStart = songSteps[selectedSongStep]?.start16ths ?? 0;
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
      announceDisplayMessage(`SONG ${song!.index + 1} PLAY`, "play");
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

  function selectSongStep(index: number) {
    const step = songSteps[index];
    if (!step) return;
    if ($isPlayingStore) stopPlayback();
    selectedSongStep = index;
    activePlaybackStep = index;
    page = Math.floor(index / STEPS_PER_PAGE);
    lastPlaybackPosition16ths = step.start16ths;
    currentTickStore.set(step.start16ths);
    dispatchProjectEdit({
      type: "set-active-scene",
      sceneIndex: step.sceneIndex,
    });
  }

  function rewindPlayback() {
    stopPlayback();
    selectSongStep(0);
    announceDisplayMessage("REWIND", "neutral");
  }

  function sceneRingProgress(
    start16ths: number,
    length16ths: number,
    isPlaying: boolean,
    currentTick: number,
  ): number {
    if (!isPlaying) return 0;
    return Math.max(0, Math.min(1, (currentTick - start16ths) / length16ths));
  }

  onDestroy(() => {
    stopPlayback();
  });
</script>

<section class="song-mode-workspace" aria-label="Song Mode preview">
  <div class="song-mode-context">
    <div>
      <p>song mode</p>
    </div>
    <div class="song-mode-status">
      <span>{songEvents.length} notes</span>
      <ProjectTempoControl tempoBpm={project.tempoBpm} {onTempoChange} />
      <span>{song?.loop ? "loop on" : "loop off"}</span>
    </div>
  </div>

  <div class="song-mode-display">
    <header class="song-mode-header">
      <span class="song-mode-mark" aria-hidden="true">⟲</span>
      <h3>song {song ? song.index + 1 : 1}</h3>
      <div class="song-mode-count">
        <span>count</span>
        <strong>{String(currentSongStep + 1).padStart(2, "0")}</strong>
      </div>
    </header>

    {#if songSteps.length > 0}
      <div class="song-grid-scroll">
        <div class="song-grid" aria-label="Song scene sequence">
          <div class="song-grid-corner"></div>
          {#each Array(8) as _, index}
            <div class="song-grid-column-label">{index + 1}</div>
          {/each}

          {#each Array(4) as _, row}
            <div class="song-grid-row-label">{pageStart + row * 8 + 1}</div>
            {#each gridSlots.slice(row * 8, row * 8 + 8) as slot}
              {#if slot}
                {@const isCurrent =
                  $isPlayingStore && slot.songStepIndex === currentSongStep}
                {@const isSelected =
                  !$isPlayingStore && slot.songStepIndex === selectedSongStep}
                <button
                  type="button"
                  class="song-scene-cell"
                  class:current={isCurrent}
                  class:selected={isSelected}
                  on:click={() => selectSongStep(slot.songStepIndex)}
                  aria-label={`Song step ${slot.songStepIndex + 1}, scene ${slot.step.sceneIndex + 1}`}
                >
                  <span
                    class="song-scene-circle"
                    style={`--scene-progress: ${sceneRingProgress(slot.step.start16ths, slot.step.length16ths, $isPlayingStore, $currentTickStore)}turn;`}
                  >
                    <span>{slot.step.sceneIndex + 1}</span>
                  </span>
                </button>
              {:else}
                <span class="song-scene-cell empty" aria-hidden="true"></span>
              {/if}
            {/each}
          {/each}
        </div>
      </div>

      <footer class="song-mode-footer">
        <div class="song-mode-transport">
          <button
            type="button"
            class="song-play"
            class:active={$isPlayingStore}
            disabled={transportState === "loading" || songEvents.length === 0}
            on:click={togglePlayback}
          >
            {$isPlayingStore
              ? "pause"
              : transportState === "loading"
                ? "load"
                : "play"}
          </button>
          <button type="button" on:click={rewindPlayback}>rew</button>
          <span>{songSteps.length} scenes</span>
        </div>
        <div class="song-page-controls">
          <button
            type="button"
            aria-label="Previous sequence page"
            disabled={page === 0}
            on:click={() => (page -= 1)}>←</button
          >
          <span>{page + 1}/{totalPages}</span>
          <button
            type="button"
            aria-label="Next sequence page"
            disabled={page >= totalPages - 1}
            on:click={() => (page += 1)}>→</button
          >
        </div>
      </footer>
    {:else}
      <div class="song-mode-empty">
        <p>No Song Mode scene chain is available in this project.</p>
      </div>
    {/if}
  </div>

  {#if playbackError}
    <p class="song-mode-error">{playbackError}</p>
  {/if}
</section>

<style>
  .song-mode-workspace {
    width: min(1180px, 100%);
    margin: 0 auto;
    padding: clamp(22px, 4vw, 54px) clamp(16px, 3vw, 34px) 40px;
  }

  .song-mode-context {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 20px;
    margin: 0 0 18px;
  }

  .song-mode-context p {
    margin: 0;
  }

  .song-mode-context p {
    color: var(--xy-text-muted);
    font-size: 11px;
    text-transform: uppercase;
  }

  .song-mode-status,
  .song-mode-transport,
  .song-page-controls {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .song-mode-status {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .song-mode-status span,
  .song-mode-transport > span,
  .song-page-controls > span {
    color: var(--xy-text-muted);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    text-transform: uppercase;
  }

  .song-mode-display {
    overflow: hidden;
    border: 1px solid #40414a;
    border-radius: 2px;
    background: #000;
    box-shadow: 0 16px 46px rgba(0, 0, 0, 0.32);
  }

  .song-mode-header {
    position: relative;
    display: grid;
    grid-template-columns: 72px 1fr 126px;
    height: 72px;
    align-items: center;
    background: #f3f1ef;
    color: #090909;
  }

  .song-mode-mark {
    display: grid;
    width: 42px;
    height: 28px;
    margin-left: 18px;
    place-items: center;
    font-size: 29px;
    font-weight: 700;
    line-height: 0;
  }

  .song-mode-header h3 {
    margin: 0;
    text-align: center;
    font-size: clamp(28px, 4vw, 42px);
    font-weight: 400;
    letter-spacing: -0.055em;
  }

  .song-mode-count {
    display: grid;
    grid-template-columns: auto 70px;
    align-items: center;
    gap: 8px;
    justify-self: end;
    margin-right: 12px;
  }

  .song-mode-count span {
    font-size: 14px;
  }

  .song-mode-count strong {
    min-width: 70px;
    border-radius: 5px;
    background: #070707;
    color: #f3f1ef;
    padding: 3px 7px 4px;
    text-align: center;
    font-family:
      ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 34px;
    font-weight: 400;
    line-height: 1;
    letter-spacing: -0.08em;
  }

  .song-grid-scroll {
    overflow-x: auto;
    background: #000;
  }

  .song-grid {
    display: grid;
    grid-template-columns: 52px repeat(8, minmax(72px, 1fr));
    grid-template-rows: 26px repeat(4, 72px);
    min-width: 648px;
  }

  .song-grid > * {
    border-right: 1px solid #343640;
    border-bottom: 1px solid #343640;
  }

  .song-grid-column-label,
  .song-grid-row-label {
    color: #73747d;
    font-size: 15px;
    font-variant-numeric: tabular-nums;
  }

  .song-grid-column-label {
    display: flex;
    align-items: center;
    padding-left: 9px;
  }

  .song-grid-row-label {
    display: flex;
    justify-content: end;
    align-items: start;
    padding: 6px 8px 0 0;
  }

  .song-grid-corner {
    background: #000;
  }

  .song-scene-cell {
    position: relative;
    display: grid;
    min-width: 0;
    min-height: 72px;
    padding: 0;
    place-items: center;
    border-radius: 0;
    border-top: 0;
    border-left: 0;
    border-right: 0;
    border-bottom: 0;
    background: #000;
    box-shadow: none;
  }

  .song-scene-cell:hover:not(:disabled),
  .song-scene-cell:focus-visible {
    background: #0b0b0d;
    outline-offset: -4px;
  }

  .song-scene-cell:active:not(:disabled) {
    transform: none;
  }

  .song-scene-circle {
    position: relative;
    display: grid;
    width: 54px;
    height: 54px;
    place-items: center;
    border-radius: 50%;
    background: conic-gradient(
      from -90deg,
      #f5f3f0 var(--scene-progress),
      #17171b 0
    );
    color: #f4f3f2;
    font-family:
      ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 28px;
    font-weight: 300;
    font-variant-numeric: tabular-nums;
    isolation: isolate;
  }

  .song-scene-circle::after {
    content: "";
    position: absolute;
    z-index: 1;
    inset: 4px;
    border-radius: inherit;
    background: var(--scene-fill, #292a33);
  }

  .song-scene-circle > span {
    position: relative;
    z-index: 2;
  }

  .song-scene-cell.current .song-scene-circle {
    --scene-fill: #30313a;
  }

  .song-scene-cell.selected .song-scene-circle {
    box-shadow: 0 0 0 3px #f5f3f0;
  }

  .song-scene-cell.empty {
    display: block;
    min-height: 72px;
    background: #000;
  }

  .song-mode-footer {
    display: flex;
    min-height: 54px;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    padding: 9px 13px;
    border-top: 1px solid #343640;
    background: #060606;
  }

  .song-mode-footer button {
    min-height: 32px;
    border-color: #33343a;
    background: #151515;
    color: #efeeec;
    box-shadow: none;
  }

  .song-mode-footer button:hover:not(:disabled) {
    background: #24242a;
    border-color: #6b6c72;
  }

  .song-mode-footer .song-play.active {
    background: #f3f1ef;
    border-color: #f3f1ef;
    color: #050505;
  }

  .song-mode-empty {
    display: grid;
    min-height: 290px;
    place-items: center;
    padding: 24px;
    color: #8b8b93;
  }

  .song-mode-error {
    margin: 10px 0 0;
    color: var(--xy-red-led);
    font-size: 12px;
  }

  @media (max-width: 680px) {
    .song-mode-context {
      align-items: start;
      flex-direction: column;
    }

    .song-mode-status {
      justify-content: flex-start;
    }

    .song-mode-header {
      grid-template-columns: 56px 1fr 102px;
      height: 60px;
    }

    .song-mode-mark {
      width: 31px;
      height: 23px;
      margin-left: 12px;
      border-width: 2px;
      font-size: 22px;
    }

    .song-mode-count {
      grid-template-columns: 1fr;
      gap: 0;
      margin-right: 8px;
      text-align: center;
    }

    .song-mode-count span {
      font-size: 10px;
    }

    .song-mode-count strong {
      min-width: 58px;
      font-size: 27px;
    }

    .song-grid-scroll {
      overflow-x: hidden;
    }

    .song-grid {
      width: 100%;
      min-width: 0;
      grid-template-columns: 30px repeat(8, minmax(0, 1fr));
      grid-template-rows: 22px repeat(4, clamp(44px, 11vw, 64px));
    }

    .song-grid-column-label,
    .song-grid-row-label {
      font-size: 11px;
    }

    .song-grid-column-label {
      justify-content: center;
      padding-left: 0;
    }

    .song-grid-row-label {
      padding: 4px 3px 0 0;
    }

    .song-scene-cell,
    .song-scene-cell.empty {
      min-height: 0;
    }

    .song-scene-circle {
      width: clamp(26px, 9vw, 42px);
      height: clamp(26px, 9vw, 42px);
      font-size: clamp(14px, 4.5vw, 22px);
    }

    .song-scene-circle::after {
      inset: 3px;
    }

    .song-scene-cell.selected .song-scene-circle {
      box-shadow: 0 0 0 2px #f5f3f0;
    }

    .song-mode-footer {
      align-items: flex-start;
      flex-direction: column;
    }

    .song-page-controls {
      align-self: flex-end;
    }
  }
</style>
