<script lang="ts">
  import type { XYProjectViewModel } from "../lib/xy/projectViewModel";
  import ArrangeWorkspace from "./ArrangeWorkspace.svelte";
  import PatternWorkspace from "./PatternWorkspace.svelte";
  import SongModeWorkspace from "./SongModeWorkspace.svelte";

  export let project: XYProjectViewModel;
  export let onTempoChange: (tempoBpm: number) => void = () => {};
  export let mode: "pattern" | "arrange" | "song" = "arrange";
</script>

<section class="created-workspace" class:pattern-mode={mode === "pattern"}>
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
</style>
