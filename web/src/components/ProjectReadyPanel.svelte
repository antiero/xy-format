<script lang="ts">
  import type {
    MidiImportOptions,
    MidiImportSummary,
  } from "../lib/xy/midiImporter";
  import type { XYProjectViewModel } from "../lib/xy/projectViewModel";
  import MidiTrackSelector from "./MidiTrackSelector.svelte";

  export let project: XYProjectViewModel;
  export let importSummary: MidiImportSummary | null;
  export let onMidiTrackSelectionChange: (
    options: MidiImportOptions,
  ) => void = () => {};
  export let midiSelectionUpdating = false;
  export let mapGmDrums = true;

  $: trackSelection = importSummary?.trackSelection ?? null;
  $: activeMapGmDrums = importSummary?.mapGmDrums ?? mapGmDrums;
</script>

<section
  class="project-ready"
  class:wide={!!trackSelection}
  aria-label="MIDI project editor"
>
  {#if trackSelection}
    <MidiTrackSelector
      {project}
      selection={trackSelection}
      selectionUpdating={midiSelectionUpdating}
      mapGmDrums={activeMapGmDrums}
      onSelectionChange={onMidiTrackSelectionChange}
    />
  {/if}
</section>

<style>
  .project-ready {
    width: min(1240px, 100%);
    margin: auto;
    padding: clamp(14px, 3vh, 28px) clamp(12px, 3vw, 32px) 36px;
  }

  .project-ready.wide {
    width: min(1280px, 100%);
  }
</style>
