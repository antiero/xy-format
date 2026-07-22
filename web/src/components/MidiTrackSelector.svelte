<script lang="ts">
  import { onDestroy } from "svelte";
  import { audioService } from "../lib/audio";
  import { webMidiOutputService } from "../lib/webMidi";
  import {
    collectSongPlaybackEvents,
    collectSongPlaybackSteps,
    crossesPlaybackPosition,
    type PlaybackEvent,
  } from "../lib/xy/playback";
  import type {
    MidiImportOptions,
    MidiTrackSelectionOption,
    MidiTrackSelectionSummary,
  } from "../lib/xy/midiImporter";
  import type { XYProjectViewModel } from "../lib/xy/projectViewModel";
  import {
    announceDisplayMessage,
    currentTickStore,
    isPlayingStore,
  } from "../stores/project";
  import MidiDrumMapToggle from "./MidiDrumMapToggle.svelte";
  import MidiOutputControl from "./MidiOutputControl.svelte";
  import MidiTrackCanvas from "./MidiTrackCanvas.svelte";

  export let project: XYProjectViewModel;
  export let selection: MidiTrackSelectionSummary;
  export let selectionUpdating = false;
  export let mapGmDrums = true;
  export let onSelectionChange: (
    options: MidiImportOptions,
  ) => void | Promise<void> = () => {};

  let animationFrame = 0;
  let lastFrameMs = 0;
  let lastPlaybackPosition16ths = 0;
  let transportState: "idle" | "loading" | "playing" = "idle";
  let playbackError = "";
  let selectionMessage = "";
  let lastSelectionKey = "";
  let pendingFitTrackIds: string[] | null = null;
  let previewTarget: "soundfont" | "opxy" = "soundfont";

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
  $: effectiveSelectedIds = new Set(
    pendingFitTrackIds ?? selection.selectedTrackIds,
  );
  $: hasDrumTracks = selection.tracks.some((track) => track.isDrum);
  $: effectiveSelectedBankCount = selectedBankCount(effectiveSelectedIds);
  $: cycleRangeValid =
    effectiveSelectedIds.size > 0 &&
    effectiveSelectedIds.size <= selection.maxInstrumentTracks &&
    effectiveSelectedBankCount <= selection.maxInstrumentTracks;
  $: {
    const key = [
      selection.selectedTrackIds.join("|"),
      selection.rangeStart16ths,
      selection.rangeEnd16ths,
      mapGmDrums,
    ].join(":");
    if (key !== lastSelectionKey) {
      lastSelectionKey = key;
      selectionMessage = "";
      pendingFitTrackIds = null;
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

  function formatBarBeat(position16ths: number): string {
    const position = Math.max(0, position16ths);
    const lastSourceBar = selection.sourceBars.at(-1);
    if (lastSourceBar && position >= lastSourceBar.end16ths) {
      return `${lastSourceBar.index + 2}.1`;
    }
    const sourceBar =
      selection.sourceBars.find(
        (bar) => bar.start16ths <= position && position < bar.end16ths,
      ) ?? lastSourceBar;
    if (!sourceBar) {
      const whole = Math.round(position);
      return `${Math.floor(whole / 16) + 1}.${Math.floor((whole % 16) / 4) + 1}`;
    }
    const beatLength16ths = 16 / sourceBar.denominator;
    const beat =
      Math.floor((position - sourceBar.start16ths) / beatLength16ths) + 1;
    return `${sourceBar.index + 1}.${Math.max(1, beat)}`;
  }

  function rebuildMidi(options: MidiImportOptions) {
    stopPlayback();
    onSelectionChange({
      selectedTrackIds: selection.selectedTrackIds,
      rangeStart16ths: selection.rangeStart16ths,
      rangeEnd16ths: selection.rangeEnd16ths,
      mapGmDrums,
      ...options,
    });
  }

  function changePreset(track: MidiTrackSelectionOption, presetId: string) {
    rebuildMidi({
      presetIdsByTrack: Object.fromEntries(
        selection.tracks.map((candidate) => [
          candidate.id,
          candidate.id === track.id ? presetId : candidate.presetId,
        ]),
      ),
    });
  }

  function midiOutputReady() {
    playbackError = "";
    announceDisplayMessage("OP-XY MIDI READY", "ok");
  }

  function midiOutputFailed(message: string) {
    playbackError = message;
    announceDisplayMessage("MIDI UNAVAILABLE", "error");
  }

  function toggleGmDrumMapping(checked: boolean) {
    rebuildMidi({ mapGmDrums: checked });
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
      pendingFitTrackIds = selectedTrackIdsFrom(next);
      selectionMessage = `Selection uses ${nextBankCount} OP-XY banks over this range; limit is ${selection.maxInstrumentTracks}.`;
      return;
    }

    pendingFitTrackIds = null;
    rebuildMidi({ selectedTrackIds: selectedTrackIdsFrom(next) });
  }

  function fitPendingSelection() {
    if (!pendingFitTrackIds) return;
    rebuildMidi({
      selectedTrackIds: pendingFitTrackIds,
      fitToCapacity: true,
    });
  }

  function changeCycleRange(start16ths: number, end16ths: number) {
    rebuildMidi({
      rangeStart16ths: start16ths,
      rangeEnd16ths: end16ths,
    });
  }

  function schedulePlaybackEvent(event: PlaybackEvent) {
    const durationMs = Math.max(30, event.duration16ths * msPer16th());
    if (previewTarget === "opxy") {
      webMidiOutputService.noteOn(event.trackIndex, event.note, event.velocity);
      webMidiOutputService.noteOff(event.trackIndex, event.note, durationMs);
    } else {
      audioService.noteOn(event.trackIndex, event.note, event.velocity);
      audioService.noteOff(event.trackIndex, event.note, durationMs);
    }
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
      webMidiOutputService.stopAll();
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
      if (previewTarget === "soundfont") {
        await audioService.ensureReady();
        for (const track of selection.tracks) {
          if (!selectedIds.has(track.id)) continue;
          for (const opXyTrackIndex of track.assignedOpXyTracks) {
            audioService.setProgram(opXyTrackIndex, track.programNumber);
          }
        }
      }
      lastPlaybackPosition16ths =
        $currentTickStore >= songLength16ths ? 0 : $currentTickStore;
      lastFrameMs = performance.now();
      isPlayingStore.set(true);
      transportState = "playing";
      animationFrame = requestAnimationFrame(playbackFrame);
      announceDisplayMessage(
        previewTarget === "opxy" ? "OP-XY PREVIEW" : "MIDI PREVIEW",
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
    webMidiOutputService.stopAll();
    isPlayingStore.set(false);
    transportState = "idle";
    lastFrameMs = 0;
  }

  function seekPlayback(position16ths: number) {
    const next = clampPlaybackPosition(position16ths);
    audioService.stopAll();
    webMidiOutputService.stopAll();
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
            : "play"}
      </button>
      <MidiOutputControl
        bind:target={previewTarget}
        disabled={selectionUpdating}
        onReady={midiOutputReady}
        onError={midiOutputFailed}
      />
      <button
        type="button"
        disabled={selectionUpdating}
        on:click={rewindPlayback}>rew</button
      >
      <span>{selection.totalBars} bars</span>
      <span
        >{formatBarBeat(selection.rangeStart16ths)}-{formatBarBeat(
          selection.rangeEnd16ths,
        )}</span
      >
      {#if hasDrumTracks}
        <MidiDrumMapToggle
          checked={mapGmDrums}
          disabled={selectionUpdating}
          onChange={toggleGmDrumMapping}
        />
      {/if}
      {#if selectionUpdating}
        <span>updating</span>
      {/if}
      {#if selectionMessage || playbackError}
        <strong>{selectionMessage || playbackError}</strong>
      {/if}
      {#if pendingFitTrackIds}
        <button
          type="button"
          class="fit-track"
          disabled={selectionUpdating}
          on:click={fitPendingSelection}>fit track</button
        >
      {/if}
      {#if selection.rangeWasAutoFit}
        <strong>Fitted to {selection.totalBars} bars</strong>
      {/if}
    </div>

    <MidiTrackCanvas
      {selection}
      {selectedIds}
      playheadActive={$isPlayingStore || $currentTickStore > 0}
      timelineLength16ths={Math.max(
        selection.sourceTotal16ths,
        selection.rangeEnd16ths,
      )}
      playheadPosition16ths={selection.rangeStart16ths +
        progress * songLength16ths}
      cycleStart16ths={selection.rangeStart16ths}
      cycleEnd16ths={selection.rangeEnd16ths}
      {cycleRangeValid}
      {selectionUpdating}
      onToggle={toggleTrack}
      onPresetChange={changePreset}
      onSeek={seekPlayback}
      onCycleChange={changeCycleRange}
    />
  </div>
</section>

<style>
  .midi-track-selector {
    display: grid;
    gap: 14px;
    width: min(1240px, 100%);
    margin: 0 auto 30px;
  }

  .selector-transport {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

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
</style>
