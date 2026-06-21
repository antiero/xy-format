<script lang="ts">
  import { get } from "svelte/store";
  import {
    activeModeStore,
    dispatchProjectEdit,
    sceneClipboardStore,
  } from "../stores/project";
  import { display16thsAsBars } from "../lib/xy/timing";
  import { SONG_MAX_CHAIN, type SongChain } from "../lib/xy/image_writer";
  import type {
    XYProjectViewModel,
    XYSceneViewModel,
  } from "../lib/xy/projectViewModel";

  export let project: XYProjectViewModel;

  let selectedSongStep = 0;

  $: scene = project.scenes[project.activeSceneIndex];
  $: song = project.songs[0] as SongChain;
  $: presentScenes = project.scenes.filter((candidate) => candidate.present);
  $: selectedSongStep = Math.max(
    0,
    Math.min(Math.max(0, song.sceneChain.length - 1), selectedSongStep),
  );
  $: selectedSongScene = song.sceneChain[selectedSongStep] ?? scene.index;

  function selectScene(sceneIndex: number) {
    dispatchProjectEdit({ type: "set-active-scene", sceneIndex });
  }

  function openPattern(trackIndex: number) {
    dispatchProjectEdit({ type: "set-active-track", trackIndex });
    activeModeStore.set("pattern");
  }

  function setScenePattern(trackIndex: number, patternIndex: number) {
    dispatchProjectEdit({
      type: "set-scene-pattern",
      sceneIndex: scene.index,
      trackIndex,
      patternIndex,
    });
  }

  function setSceneMute(trackIndex: number, muted: boolean) {
    dispatchProjectEdit({
      type: "set-scene-mute",
      sceneIndex: scene.index,
      trackIndex,
      muted,
    });
  }

  function copyScene(current: XYSceneViewModel) {
    sceneClipboardStore.set({
      patternByTrack: [...current.patternByTrack],
      mutedTracks: [...current.mutedTracks],
    });
  }

  function pasteScene() {
    const clipboard = get(sceneClipboardStore);
    if (!clipboard) return;
    clipboard.patternByTrack.forEach((patternIndex, trackIndex) => {
      dispatchProjectEdit({
        type: "set-scene-pattern",
        sceneIndex: scene.index,
        trackIndex,
        patternIndex,
      });
    });
    clipboard.mutedTracks.forEach((muted, trackIndex) => {
      dispatchProjectEdit({
        type: "set-scene-mute",
        sceneIndex: scene.index,
        trackIndex,
        muted,
      });
    });
  }

  function duplicateScene() {
    const target = Math.min(98, scene.index + 1);
    dispatchProjectEdit({
      type: "duplicate-scene",
      sourceSceneIndex: scene.index,
      targetSceneIndex: target,
    });
    selectScene(target);
  }

  function resetScene() {
    dispatchProjectEdit({ type: "reset-scene", sceneIndex: scene.index });
  }

  function updateSong(sceneChain: number[], loop = song.loop) {
    dispatchProjectEdit({
      type: "update-song-chain",
      songIndex: 0,
      sceneChain,
      loop,
    });
  }

  function addActiveSceneToSong() {
    if (song.sceneChain.length >= SONG_MAX_CHAIN) return;
    updateSong([...song.sceneChain, scene.index]);
    selectedSongStep = song.sceneChain.length;
  }

  function setSongStepScene(sceneIndex: number) {
    if (song.sceneChain.length === 0) return;
    const next = [...song.sceneChain];
    next[selectedSongStep] = sceneIndex;
    updateSong(next);
    selectScene(sceneIndex);
  }

  function removeSongStep(index: number) {
    updateSong(song.sceneChain.filter((_, i) => i !== index));
    selectedSongStep = Math.max(0, index - 1);
  }

  function moveSongStep(index: number, delta: number) {
    const next = [...song.sceneChain];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    const [item] = next.splice(index, 1);
    next.splice(target, 0, item);
    updateSong(next);
    selectedSongStep = target;
  }
</script>

<section class="workspace arrange-workspace">
  <div class="workspace-head">
    <div>
      <p class="eyebrow">Arrange</p>
      <h2>Scene {scene.index + 1}</h2>
    </div>
    <div class="status-strip">
      <span>{scene.present ? "present" : "empty"}</span>
      <span>{display16thsAsBars(scene.length16ths)}</span>
      <span>{song.sceneChain.length}/{SONG_MAX_CHAIN} song</span>
    </div>
  </div>

  <div class="arrange-focus-layout">
    <aside class="scene-bank-panel">
      <div class="section-title">
        <span>scenes</span>
        <span>{presentScenes.length}/99 present</span>
      </div>

      <div class="scene-action-row">
        <button type="button" on:click={() => copyScene(scene)}>copy</button>
        <button type="button" on:click={pasteScene}>paste</button>
        <button type="button" on:click={duplicateScene}>clone</button>
        <button type="button" on:click={resetScene}>reset</button>
      </div>

      <div class="scene-present-strip">
        {#if presentScenes.length === 0}
          <span>none</span>
        {:else}
          {#each presentScenes as candidate}
            <button
              type="button"
              class:active={candidate.index === scene.index}
              on:click={() => selectScene(candidate.index)}
            >
              {candidate.index + 1}
            </button>
          {/each}
        {/if}
      </div>

      <div class="scene-keypad" aria-label="Scene bank">
        {#each project.scenes as candidate}
          <button
            type="button"
            class:active={candidate.index === scene.index}
            class:present={candidate.present}
            on:click={() => selectScene(candidate.index)}
            title={`scene ${candidate.index + 1}`}
          >
            <span>{candidate.index + 1}</span>
            <i
              >{candidate.present
                ? display16thsAsBars(candidate.length16ths)
                : ""}</i
            >
          </button>
        {/each}
      </div>
    </aside>

    <div class="scene-detail-panel">
      <div class="section-title">
        <span>scene {scene.index + 1}</span>
        <span>{display16thsAsBars(scene.length16ths)}</span>
      </div>

      <div class="scene-track-editor">
        {#each project.tracks as track}
          {@const patternIndex = scene.patternByTrack[track.index]}
          {@const pattern = track.patterns[patternIndex]}
          <div
            class="arrange-track-row"
            class:muted={scene.mutedTracks[track.index]}
          >
            <button
              type="button"
              class="arrange-track-id"
              on:click={() => openPattern(track.index)}
            >
              <span class="track-led" class:red={track.colorRole === "red"}
              ></span>
              <strong>{track.label}</strong>
            </button>
            <select
              value={patternIndex}
              on:change={(event) =>
                setScenePattern(
                  track.index,
                  Number((event.target as HTMLSelectElement).value),
                )}
            >
              {#each track.patterns as candidate}
                <option value={candidate.index}>P{candidate.index + 1}</option>
              {/each}
            </select>
            <span>{pattern ? `${pattern.notes.length} notes` : "missing"}</span>
            <span>{pattern ? pattern.trackScaleLabel : "-"}</span>
            <button
              type="button"
              class:active={scene.mutedTracks[track.index]}
              on:click={() =>
                setSceneMute(track.index, !scene.mutedTracks[track.index])}
            >
              {scene.mutedTracks[track.index] ? "muted" : "on"}
            </button>
          </div>
        {/each}
      </div>
    </div>

    <aside class="song-flow-panel">
      <div class="section-title">
        <span>song 1</span>
        <span
          >{song.supported
            ? song.loop
              ? "loop on"
              : "loop off"
            : "read-only"}</span
        >
      </div>

      {#if song.supported}
        <div class="song-controls">
          <button
            type="button"
            on:click={addActiveSceneToSong}
            disabled={song.sceneChain.length >= SONG_MAX_CHAIN}
            >add scene {scene.index + 1}</button
          >
          <button
            type="button"
            class:active={song.loop}
            on:click={() => updateSong(song.sceneChain, !song.loop)}
            >{song.loop ? "loop on" : "loop off"}</button
          >
        </div>

        <div class="song-ribbon">
          {#if song.sceneChain.length === 0}
            <p class="empty-line">No scenes in Song 1.</p>
          {:else}
            {#each song.sceneChain as sceneIndex, index}
              <button
                type="button"
                class:active={index === selectedSongStep}
                on:click={() => {
                  selectedSongStep = index;
                  selectScene(sceneIndex);
                }}
              >
                <span>{index + 1}</span>
                <strong>{sceneIndex + 1}</strong>
              </button>
            {/each}
          {/if}
        </div>

        {#if song.sceneChain.length > 0}
          <div class="song-step-editor">
            <div class="section-title">
              <span>step {selectedSongStep + 1}</span>
              <span>scene {selectedSongScene + 1}</span>
            </div>
            <select
              value={selectedSongScene}
              on:change={(event) =>
                setSongStepScene(
                  Number((event.target as HTMLSelectElement).value),
                )}
            >
              {#each project.scenes as candidate}
                <option value={candidate.index}
                  >scene {candidate.index + 1}</option
                >
              {/each}
            </select>
            <div class="action-row">
              <button
                type="button"
                on:click={() => moveSongStep(selectedSongStep, -1)}
                disabled={selectedSongStep === 0}>up</button
              >
              <button
                type="button"
                on:click={() => moveSongStep(selectedSongStep, 1)}
                disabled={selectedSongStep === song.sceneChain.length - 1}
                >down</button
              >
              <button
                type="button"
                on:click={() => removeSongStep(selectedSongStep)}>remove</button
              >
            </div>
          </div>
        {/if}
      {:else}
        <p class="empty-line">
          Song footer shape is not supported for web editing.
        </p>
      {/if}
    </aside>
  </div>
</section>
