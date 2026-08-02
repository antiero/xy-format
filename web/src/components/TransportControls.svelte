<script lang="ts">
  export let isPlaying = false;
  export let loading = false;
  export let playDisabled = false;
  export let stopDisabled = false;
  export let playLabel = "Play";
  export let stopLabel = "Stop";
  export let onPlay: () => void | Promise<void> = () => {};
  export let onStop: () => void = () => {};
</script>

<div class="transport-controls" aria-label="Playback controls">
  <button
    type="button"
    class="transport-icon transport-play"
    class:active={isPlaying}
    disabled={playDisabled || loading || isPlaying}
    aria-label={loading ? "Loading playback" : playLabel}
    title={loading ? "Loading playback" : playLabel}
    on:click={onPlay}
  >
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <path d="M4 2.75 13 8l-9 5.25z"></path>
    </svg>
  </button>
  <button
    type="button"
    class="transport-icon transport-stop"
    disabled={stopDisabled}
    aria-label={stopLabel}
    title={stopLabel}
    on:click={onStop}
  >
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <rect x="3.25" y="3.25" width="9.5" height="9.5"></rect>
    </svg>
  </button>
</div>

<style>
  .transport-controls {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }

  .transport-icon {
    display: grid;
    width: 31px;
    min-width: 31px;
    height: 31px;
    min-height: 31px;
    padding: 0;
    place-items: center;
  }

  .transport-icon svg {
    width: 14px;
    height: 14px;
    fill: currentColor;
  }

  .transport-play.active {
    color: var(--xy-good);
  }
</style>
