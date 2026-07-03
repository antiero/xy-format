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

  $: trackSelection = importSummary?.trackSelection ?? null;
  $: showMidiEditor =
    !!trackSelection &&
    (trackSelection.isSelectionRecommended ||
      trackSelection.rangeStart16ths > 0 ||
      trackSelection.rangeEnd16ths < trackSelection.sourceTotal16ths ||
      trackSelection.tracks.length > trackSelection.maxInstrumentTracks);
</script>

<section
  class="project-ready"
  class:wide={showMidiEditor}
  aria-label="MIDI project editor"
>
  {#if showMidiEditor && trackSelection}
    <MidiTrackSelector
      {project}
      selection={trackSelection}
      selectionUpdating={midiSelectionUpdating}
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
