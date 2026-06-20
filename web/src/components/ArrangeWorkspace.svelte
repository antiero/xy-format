<script lang="ts">
  import { get } from 'svelte/store';
  import { dispatchProjectEdit, sceneClipboardStore } from '../stores/project';
  import { display16thsAsBars } from '../lib/xy/timing';
  import { SONG_MAX_CHAIN, type SongChain } from '../lib/xy/image_writer';
  import type { XYProjectViewModel, XYSceneViewModel } from '../lib/xy/projectViewModel';

  export let project: XYProjectViewModel;

  $: scene = project.scenes[project.activeSceneIndex];
  $: song = project.songs[0] as SongChain;

  function selectScene(sceneIndex: number) {
    dispatchProjectEdit({ type: 'set-active-scene', sceneIndex });
  }

  function setScenePattern(trackIndex: number, patternIndex: number) {
    dispatchProjectEdit({
      type: 'set-scene-pattern',
      sceneIndex: scene.index,
      trackIndex,
      patternIndex,
    });
  }

  function setSceneMute(trackIndex: number, muted: boolean) {
    dispatchProjectEdit({
      type: 'set-scene-mute',
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
        type: 'set-scene-pattern',
        sceneIndex: scene.index,
        trackIndex,
        patternIndex,
      });
    });
    clipboard.mutedTracks.forEach((muted, trackIndex) => {
      dispatchProjectEdit({
        type: 'set-scene-mute',
        sceneIndex: scene.index,
        trackIndex,
        muted,
      });
    });
  }

  function duplicateScene() {
    const target = Math.min(98, scene.index + 1);
    dispatchProjectEdit({
      type: 'duplicate-scene',
      sourceSceneIndex: scene.index,
      targetSceneIndex: target,
    });
  }

  function resetScene() {
    dispatchProjectEdit({ type: 'reset-scene', sceneIndex: scene.index });
  }

  function updateSong(sceneChain: number[], loop = song.loop) {
    dispatchProjectEdit({
      type: 'update-song-chain',
      songIndex: 0,
      sceneChain,
      loop,
    });
  }

  function addActiveSceneToSong() {
    if (song.sceneChain.length >= SONG_MAX_CHAIN) return;
    updateSong([...song.sceneChain, scene.index]);
  }

  function removeSongStep(index: number) {
    updateSong(song.sceneChain.filter((_, i) => i !== index));
  }

  function moveSongStep(index: number, delta: number) {
    const next = [...song.sceneChain];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    const [item] = next.splice(index, 1);
    next.splice(target, 0, item);
    updateSong(next);
  }
</script>

<section class="workspace arrange-workspace">
  <div class="workspace-head">
    <div>
      <p class="eyebrow">Arrange</p>
      <h2>Scene {scene.index + 1}</h2>
    </div>
    <div class="status-strip">
      <span>{scene.present ? 'present' : 'empty'}</span>
      <span>{display16thsAsBars(scene.length16ths)}</span>
      <span>{song.sceneChain.length}/{SONG_MAX_CHAIN} song steps</span>
    </div>
  </div>

  <div class="arrange-layout">
    <div class="scene-matrix-panel">
      <div class="section-title">
        <span>scene matrix</span>
        <span>99 scenes · 16 tracks</span>
      </div>
      <div class="scene-matrix">
        <div class="matrix-header">
          <span>scene</span>
          {#each project.tracks as track}
            <span>{track.label}</span>
          {/each}
        </div>
        {#each project.scenes as row}
          <button
            type="button"
            class="matrix-row"
            class:active={row.index === scene.index}
            class:present={row.present}
            on:click={() => selectScene(row.index)}
          >
            <span class="scene-number">
              <i class="track-led" class:red={row.present}></i>
              {row.index + 1}
            </span>
            {#each row.patternByTrack as patternIndex, trackIndex}
              <span class="matrix-cell" class:muted={row.mutedTracks[trackIndex]}>
                P{patternIndex + 1}
              </span>
            {/each}
          </button>
        {/each}
      </div>
    </div>

    <aside class="scene-inspector">
      <div class="section-title">
        <span>scene inspector</span>
        <span>{display16thsAsBars(scene.length16ths)}</span>
      </div>
      <div class="action-row">
        <button type="button" on:click={() => copyScene(scene)}>copy</button>
        <button type="button" on:click={pasteScene}>paste</button>
        <button type="button" on:click={duplicateScene}>duplicate</button>
        <button type="button" on:click={resetScene}>reset</button>
      </div>

      <div class="scene-track-list">
        {#each project.tracks as track}
          <div class="scene-track-row">
            <span>{track.label}</span>
            <select value={scene.patternByTrack[track.index]} on:change={(event) => setScenePattern(track.index, Number((event.target as HTMLSelectElement).value))}>
              {#each track.patterns as pattern}
                <option value={pattern.index}>P{pattern.index + 1}</option>
              {/each}
            </select>
            <label class="mute-toggle">
              <input
                type="checkbox"
                checked={scene.mutedTracks[track.index]}
                on:change={(event) => setSceneMute(track.index, (event.target as HTMLInputElement).checked)}
              />
              mute
            </label>
          </div>
        {/each}
      </div>
    </aside>

    <aside class="song-editor">
      <div class="section-title">
        <span>song 1</span>
        <span>{song.supported ? (song.loop ? 'loop on' : 'loop off') : 'read-only'}</span>
      </div>
      {#if song.supported}
        <div class="action-row">
          <button type="button" on:click={addActiveSceneToSong} disabled={song.sceneChain.length >= SONG_MAX_CHAIN}>add scene {scene.index + 1}</button>
          <label class="mute-toggle">
            <input type="checkbox" checked={song.loop} on:change={(event) => updateSong(song.sceneChain, (event.target as HTMLInputElement).checked)} />
            loop
          </label>
        </div>
        <div class="song-chain">
          {#if song.sceneChain.length === 0}
            <p class="empty-line">No scenes in Song 1.</p>
          {:else}
            {#each song.sceneChain as sceneIndex, i}
              <div class="song-step">
                <span>{i + 1}</span>
                <select value={sceneIndex} on:change={(event) => {
                  const next = [...song.sceneChain];
                  next[i] = Number((event.target as HTMLSelectElement).value);
                  updateSong(next);
                }}>
                  {#each project.scenes as candidate}
                    <option value={candidate.index}>scene {candidate.index + 1}</option>
                  {/each}
                </select>
                <button type="button" on:click={() => moveSongStep(i, -1)} disabled={i === 0}>up</button>
                <button type="button" on:click={() => moveSongStep(i, 1)} disabled={i === song.sceneChain.length - 1}>down</button>
                <button type="button" on:click={() => removeSongStep(i)}>remove</button>
              </div>
            {/each}
          {/if}
        </div>
      {:else}
        <p class="empty-line">Song footer shape is not supported for web editing.</p>
      {/if}
    </aside>
  </div>
</section>
