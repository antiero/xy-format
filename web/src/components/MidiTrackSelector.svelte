<script lang="ts">
  import { onDestroy } from "svelte";
  import { audioService } from "../lib/audio";
  import {
    collectSongPlaybackEvents,
    collectSongPlaybackSteps,
    crossesPlaybackPosition,
    type PlaybackEvent,
  } from "../lib/xy/playback";
  import type {
    MidiTrackSelectionOption,
    MidiTrackSelectionSummary,
  } from "../lib/xy/midiImporter";
  import type { XYProjectViewModel } from "../lib/xy/projectViewModel";
  import {
    announceDisplayMessage,
    currentTickStore,
    isPlayingStore,
  } from "../stores/project";
  import MidiTrackCanvas from "./MidiTrackCanvas.svelte";

  export let project: XYProjectViewModel;
  export let selection: MidiTrackSelectionSummary;
  export let selectionUpdating = false;
  export let onSelectionChange: (
    trackIds: string[],
  ) => void | Promise<void> = () => {};

  let animationFrame = 0;
  let lastFrameMs = 0;
  let lastPlaybackPosition16ths = 0;
  let transportState: "idle" | "loading" | "playing" = "idle";
  let playbackError = "";
  let selectionMessage = "";
  let lastSelectionKey = "";

  $: selectedIds = new Set(selection.selectedTrackIds);
  $: song = project.songs[0];
  $: songSteps =
    song?.supported && song.sceneChain.length > 0
      ? collectSongPlaybackSteps(project, song.sceneChain)
      : [];
  $: songEvents = collectSongPlaybackEvents(project, songSteps);
  $: songLength16ths = songSteps.reduce(
    (length, step) => length + step.length16ths,
    0,
  );
  $: progress =
    songLength16ths > 0
      ? Math.max(0, Math.min(1, $currentTickStore / songLength16ths))
      : 0;
  $: selectedTrackCount = selection.tracks.filter((track) =>
    selectedIds.has(track.id),
  ).length;
  $: {
    const key = selection.selectedTrackIds.join("|");
    if (key !== lastSelectionKey) {
      lastSelectionKey = key;
      selectionMessage = "";
    }
  }

  function msPer16th(): number {
    return 15000 / Math.max(10, project.tempoBpm || 120);
  }

  function clampPlaybackPosition(position16ths: number): number {
    if (songLength16ths <= 0) return 0;
    return Math.max(0, Math.min(songLength16ths - 1 / 64, position16ths));
  }

  function selectedBankCount(ids: Set<string>): number {
    return selection.tracks.reduce(
      (sum, track) => sum + (ids.has(track.id) ? track.bankCount : 0),
      0,
    );
  }

  function selectedTrackIdsFrom(ids: Set<string>): string[] {
    return selection.tracks
      .filter((track) => ids.has(track.id))
      .map((track) => track.id);
  }

  function toggleTrack(track: MidiTrackSelectionOption) {
    const next = new Set(selectedIds);
    if (next.has(track.id)) {
      next.delete(track.id);
    } else {
      next.add(track.id);
    }

    const nextTrackCount = next.size;
    const nextBankCount = selectedBankCount(next);
    if (nextTrackCount === 0) {
      selectionMessage = "Keep at least one MIDI track selected.";
      return;
    }
    if (
      nextTrackCount > selection.maxInstrumentTracks ||
      nextBankCount > selection.maxInstrumentTracks
    ) {
      selectionMessage = `Selection uses ${nextBankCount} OP-XY banks; limit is ${selection.maxInstrumentTracks}.`;
      return;
    }

    stopPlayback();
    onSelectionChange(selectedTrackIdsFrom(next));
  }

  function schedulePlaybackEvent(event: PlaybackEvent) {
    const durationMs = Math.max(30, event.duration16ths * msPer16th());
    audioService.noteOn(event.trackIndex, event.note, event.velocity);
    audioService.noteOff(event.trackIndex, event.note, durationMs);
  }

  function playbackFrame(now: number) {
    if (!$isPlayingStore || songLength16ths <= 0) return;
    if (!lastFrameMs) lastFrameMs = now;

    const previous = lastPlaybackPosition16ths;
    let next = previous + (now - lastFrameMs) / msPer16th();
    lastFrameMs = now;
    let didWrap = false;

    if (next >= songLength16ths) {
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
    animationFrame = requestAnimationFrame(playbackFrame);
  }

  async function togglePlayback() {
    if ($isPlayingStore) {
      stopPlayback();
      announceDisplayMessage("STOP", "neutral");
      return;
    }
    if (songEvents.length === 0) return;

    playbackError = "";
    transportState = "loading";
    try {
      await audioService.ensureReady();
      lastPlaybackPosition16ths =
        $currentTickStore >= songLength16ths ? 0 : $currentTickStore;
      lastFrameMs = performance.now();
      isPlayingStore.set(true);
      transportState = "playing";
      animationFrame = requestAnimationFrame(playbackFrame);
      announceDisplayMessage("MIDI PREVIEW", "play");
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

  function seekPlayback(position16ths: number) {
    const next = clampPlaybackPosition(position16ths);
    audioService.stopAll();
    lastPlaybackPosition16ths = next;
    currentTickStore.set(next);

    if ($isPlayingStore) {
      lastFrameMs = performance.now();
      if (!animationFrame) {
        animationFrame = requestAnimationFrame(playbackFrame);
      }
    }
  }

  function rewindPlayback() {
    stopPlayback();
    lastPlaybackPosition16ths = 0;
    currentTickStore.set(0);
    announceDisplayMessage("REWIND", "neutral");
  }

  onDestroy(() => {
    stopPlayback();
  });
</script>

<section class="midi-track-selector" aria-label="MIDI track selection">
  <header class="selector-head">
    <div>
      <p>MIDI Editor</p>
      <h2>Set tracks for OP-XY project.</h2>
    </div>
    <div class="selector-status" aria-live="polite">
      <span>{selectedTrackCount}/{selection.maxInstrumentTracks} tracks</span>
      <span
        >{selection.selectedBankCount}/{selection.maxInstrumentTracks}
        banks</span
      >
      <span>{songEvents.length} notes</span>
    </div>
  </header>

  {#if selection.warning}
    <p class="selector-warning">{selection.warning}</p>
  {/if}

  <div class="selector-console">
    <div class="selector-transport">
      <button
        type="button"
        class="transport-play"
        class:active={$isPlayingStore}
        disabled={selectionUpdating ||
          transportState === "loading" ||
          songEvents.length === 0}
        on:click={togglePlayback}
      >
        {$isPlayingStore
          ? "stop"
          : transportState === "loading"
            ? "load"
            : "play selected"}
      </button>
      <button
        type="button"
        disabled={selectionUpdating}
        on:click={rewindPlayback}>rew</button
      >
      <span>{project.tempoBpm.toFixed(1)} bpm</span>
      <span>{selection.totalBars} bars</span>
      {#if selectionUpdating}
        <span>updating</span>
      {/if}
      {#if selectionMessage || playbackError}
        <strong>{selectionMessage || playbackError}</strong>
      {/if}
    </div>

    <MidiTrackCanvas
      {selection}
      {selectedIds}
      {progress}
      playheadActive={$isPlayingStore || $currentTickStore > 0}
      timelineLength16ths={songLength16ths}
      {selectionUpdating}
      onToggle={toggleTrack}
      onSeek={seekPlayback}
    />
  </div>
</section>

<style>
  .midi-track-selector {
    display: grid;
    gap: 14px;
    width: min(1240px, 100%);
    margin: 28px auto 30px;
  }

  .selector-head {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 16px;
  }

  .selector-head p,
  .selector-head h2,
  .selector-warning {
    margin: 0;
  }

  .selector-head p {
    color: var(--xy-text-muted);
    font-size: 11px;
    text-transform: uppercase;
  }

  .selector-head h2 {
    margin-top: 5px;
    font-size: clamp(20px, 3vw, 30px);
    font-weight: 520;
    letter-spacing: 0;
  }

  .selector-status,
  .selector-transport {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .selector-status {
    justify-content: flex-end;
  }

  .selector-status span,
  .selector-transport span,
  .selector-transport strong {
    border: 1px solid #313131;
    background: #0a0a0a;
    color: var(--xy-text-muted);
    padding: 6px 8px;
    font-size: 10px;
    font-variant-numeric: tabular-nums;
    text-transform: uppercase;
  }

  .selector-transport strong {
    color: var(--xy-yellow-warn);
    font-weight: 560;
  }

  .selector-warning {
    color: var(--xy-yellow-warn);
    font-size: 12px;
    line-height: 1.45;
    text-transform: uppercase;
  }

  .selector-console {
    overflow: hidden;
    border: 1px solid #3f3f3f;
    border-radius: 3px;
    background: #050505;
    box-shadow: 0 18px 42px rgba(0, 0, 0, 0.34);
  }

  .selector-transport {
    min-height: 48px;
    padding: 8px 10px;
    border-bottom: 1px solid #303030;
    background: #101010;
  }

  @media (max-width: 760px) {
    .selector-head {
      align-items: start;
      flex-direction: column;
    }
  }
</style>
