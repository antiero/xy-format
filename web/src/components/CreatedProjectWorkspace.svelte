<script lang="ts">
  import type { XYProjectViewModel } from "../lib/xy/projectViewModel";
  import ArrangeWorkspace from "./ArrangeWorkspace.svelte";
  import SongModeWorkspace from "./SongModeWorkspace.svelte";

  export let project: XYProjectViewModel;
  export let onTempoChange: (tempoBpm: number) => void = () => {};

  let mode: "arrange" | "song" = "arrange";
</script>

<section class="created-workspace">
  <nav class="view-toggle" aria-label="Playback view">
    <button
      type="button"
      class:active={mode === "arrange"}
      aria-pressed={mode === "arrange"}
      on:click={() => (mode = "arrange")}>Arrange</button
    >
    <button
      type="button"
      class:active={mode === "song"}
      aria-pressed={mode === "song"}
      on:click={() => (mode = "song")}>Song</button
    >
  </nav>

  {#if mode === "arrange"}
    <ArrangeWorkspace {project} {onTempoChange} />
  {:else}
    <SongModeWorkspace {project} {onTempoChange} />
  {/if}
</section>

<style>
  .created-workspace {
    min-width: 0;
  }

  .view-toggle {
    display: flex;
    justify-content: center;
    gap: 6px;
    padding: 14px 18px 0;
  }

  .view-toggle button {
    min-width: 92px;
    min-height: 30px;
    border-color: #33343a;
    background: #101010;
    color: #aeb0b6;
    box-shadow: none;
  }

  .view-toggle button.active {
    border-color: #f3f1ef;
    background: #f3f1ef;
    color: #050505;
  }
</style>
