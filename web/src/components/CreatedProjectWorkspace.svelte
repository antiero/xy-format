<script lang="ts">
  import type { XYProjectViewModel } from "../lib/xy/projectViewModel";
  import ArrangeWorkspace from "./ArrangeWorkspace.svelte";
  import PatternWorkspace from "./PatternWorkspace.svelte";
  import SongModeWorkspace from "./SongModeWorkspace.svelte";

  export let project: XYProjectViewModel;
  export let onTempoChange: (tempoBpm: number) => void = () => {};

  let mode: "pattern" | "arrange" | "song" = "arrange";
</script>

<section class="created-workspace" class:pattern-mode={mode === "pattern"}>
  <nav class="view-toggle" aria-label="Project view">
    <button
      type="button"
      class:active={mode === "pattern"}
      aria-pressed={mode === "pattern"}
      title="Edit notes, timing, track scale, and step data"
      on:click={() => (mode = "pattern")}>Pattern</button
    >
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

  {#if mode === "pattern"}
    <PatternWorkspace {project} />
  {:else if mode === "arrange"}
    <ArrangeWorkspace {project} {onTempoChange} />
  {:else}
    <SongModeWorkspace {project} {onTempoChange} />
  {/if}
</section>

<style>
  .created-workspace {
    display: flex;
    flex: 1;
    min-width: 0;
    min-height: 0;
    flex-direction: column;
  }

  .created-workspace.pattern-mode {
    overflow: hidden;
  }

  .view-toggle {
    display: flex;
    flex: none;
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
