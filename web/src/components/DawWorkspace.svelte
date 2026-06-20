<script lang="ts">
  import { onDestroy } from 'svelte';
  import { audioService } from '../lib/audio';
  import {
    collectLanePlaybackEvents,
    collectScenePlaybackLanes,
    crossesPlaybackPosition,
    laneLoopLength16ths,
    type PlaybackEvent,
  } from '../lib/xy/playback';
  import { display16thsAsBars } from '../lib/xy/timing';
  import { currentTickStore, dispatchProjectEdit, isPlayingStore } from '../stores/project';
  import type { XYProjectViewModel } from '../lib/xy/projectViewModel';

  export let project: XYProjectViewModel;

  const LANE_HEADER_WIDTH = 320;

  let mutedTracks = new Set<number>();
  let soloTracks = new Set<number>();
  let animationFrame = 0;
  let lastFrameMs = 0;
  let lastPlaybackPosition16ths = 0;
  let transportState: 'idle' | 'loading' | 'playing' = 'idle';
  let playbackError = '';

  $: scene = project.scenes[project.activeSceneIndex];
  $: lanes = collectScenePlaybackLanes(project, scene.index);
  $: playbackEvents = collectLanePlaybackEvents(lanes, mutedTracks, soloTracks);
  $: loopLength16ths = Math.max(scene.length16ths || 16, laneLoopLength16ths(lanes));
  $: laneWidth = Math.max(760, loopLength16ths * 24);
  $: progress = loopLength16ths > 0 ? Math.min(1, $currentTickStore / loopLength16ths) : 0;
  $: ignoredTracks = project.tracks.filter((track) => !lanes.some((lane) => lane.trackIndex === track.index));
  $: activeLaneCount = lanes.filter((lane) => !lane.sceneMuted && !mutedTracks.has(lane.trackIndex) && (soloTracks.size === 0 || soloTracks.has(lane.trackIndex))).length;

  function msPer16th(): number {
    return 15000 / Math.max(10, project.tempoBpm || 120);
  }

  function selectScene(sceneIndex: number) {
    stopPlayback();
    mutedTracks = new Set();
    soloTracks = new Set();
    dispatchProjectEdit({ type: 'set-active-scene', sceneIndex });
  }

  function toggleSet(source: Set<number>, value: number): Set<number> {
    const next = new Set(source);
    if (next.has(value)) {
      next.delete(value);
    } else {
      next.add(value);
    }
    return next;
  }

  function toggleMute(trackIndex: number) {
    mutedTracks = toggleSet(mutedTracks, trackIndex);
  }

  function toggleSolo(trackIndex: number) {
    soloTracks = toggleSet(soloTracks, trackIndex);
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
      return;
    }

    playbackError = '';
    transportState = 'loading';
    try {
      await audioService.ensureReady();
      lastPlaybackPosition16ths = $currentTickStore >= loopLength16ths ? 0 : $currentTickStore;
      lastFrameMs = performance.now();
      isPlayingStore.set(true);
      transportState = 'playing';
      animationFrame = requestAnimationFrame(playbackFrame);
    } catch (error) {
      transportState = 'idle';
      isPlayingStore.set(false);
      playbackError = error instanceof Error ? error.message : 'audio unavailable';
    }
  }

  function stopPlayback() {
    if (animationFrame) {
      cancelAnimationFrame(animationFrame);
      animationFrame = 0;
    }
    audioService.stopAll();
    isPlayingStore.set(false);
    transportState = 'idle';
    lastFrameMs = 0;
  }

  function rewindPlayback() {
    stopPlayback();
    lastPlaybackPosition16ths = 0;
    currentTickStore.set(0);
  }

  onDestroy(() => {
    stopPlayback();
  });
</script>

<section class="workspace daw-workspace">
  <div class="workspace-head daw-head">
    <div>
      <p class="eyebrow">DAW</p>
      <h2>Scene {scene.index + 1}</h2>
    </div>
    <div class="status-strip">
      <span>{activeLaneCount} lanes</span>
      <span>{playbackEvents.length} notes</span>
      <span>{display16thsAsBars(loopLength16ths)}</span>
    </div>
  </div>

  <div class="daw-console">
    <div class="daw-transport">
      <div class="transport-controls">
        <button
          type="button"
          class="transport-play"
          class:active={$isPlayingStore}
          disabled={transportState === 'loading' || playbackEvents.length === 0}
          on:click={togglePlayback}
        >
          {$isPlayingStore ? 'stop' : transportState === 'loading' ? 'load' : 'play all'}
        </button>
        <button type="button" on:click={rewindPlayback}>rew</button>
      </div>

      <label class="daw-scene-select">
        <span>scene</span>
        <select value={scene.index} on:change={(event) => selectScene(Number((event.target as HTMLSelectElement).value))}>
          {#each project.scenes as candidate}
            <option value={candidate.index}>scene {candidate.index + 1}{candidate.present ? '' : ' · empty'}</option>
          {/each}
        </select>
      </label>

      <div class="transport-readout">
        <span>{project.tempoBpm.toFixed(1)} bpm</span>
        <span>{activeLaneCount}/{lanes.length} active</span>
        <span>{ignoredTracks.length} ignored</span>
      </div>

      <div class="transport-meter" aria-hidden="true">
        <span style={`width: ${progress * 100}%;`}></span>
      </div>
      {#if playbackError}
        <span class="transport-error">{playbackError}</span>
      {/if}
    </div>

    <div class="daw-lanes">
      <div class="daw-timeline">
        <div class="daw-track-spacer">tracks</div>
        <div class="daw-bars" style={`width: ${laneWidth}px;`}>
          {#each Array(Math.ceil(loopLength16ths / 16)) as _, bar}
            <span style={`left: ${(bar * 16 / loopLength16ths) * 100}%;`}>B{bar + 1}</span>
          {/each}
        </div>
      </div>

      {#if lanes.length === 0}
        <div class="daw-empty">
          <span class="track-led red"></span>
          <p>No step data in this scene.</p>
        </div>
      {:else}
        {#each lanes as lane}
          <div
            class="daw-lane"
            class:scene-muted={lane.sceneMuted}
            class:muted={mutedTracks.has(lane.trackIndex)}
            class:soloed={soloTracks.has(lane.trackIndex)}
          >
            <div class="daw-lane-label">
              <span class="track-led" class:red={lane.colorRole === 'red'}></span>
              <strong>{lane.trackLabel}</strong>
              <span>{lane.patternLabel}</span>
              <span>{lane.noteCount}</span>
              <span>{lane.scaleLabel}</span>
              <button type="button" class:active={mutedTracks.has(lane.trackIndex)} on:click={() => toggleMute(lane.trackIndex)}>mute</button>
              <button type="button" class:active={soloTracks.has(lane.trackIndex)} on:click={() => toggleSolo(lane.trackIndex)}>solo</button>
            </div>
            <div class="daw-lane-roll" style={`width: ${laneWidth}px;`}>
              <span
                class="daw-lane-length"
                style={`width: ${(lane.length16ths / loopLength16ths) * 100}%;`}
              ></span>
              {#each lane.events as event}
                <button
                  type="button"
                  class="daw-note"
                  style={`left: ${(event.start16ths / loopLength16ths) * 100}%; width: ${Math.max(3, (event.duration16ths / loopLength16ths) * 100)}%;`}
                  title={`${lane.trackLabel} ${lane.patternLabel} · note ${event.note}`}
                ></button>
              {/each}
            </div>
          </div>
        {/each}
      {/if}

      <div
        class="daw-playhead"
        class:active={$isPlayingStore || $currentTickStore > 0}
        style={`left: ${LANE_HEADER_WIDTH + progress * laneWidth}px;`}
      ></div>
    </div>

    {#if ignoredTracks.length > 0}
      <div class="ignored-tracks">
        <span>ignored empty</span>
        {#each ignoredTracks as track}
          <i>{track.label}</i>
        {/each}
      </div>
    {/if}
  </div>
</section>
