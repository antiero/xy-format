<script lang="ts">
  import type { MidiImportSummary } from "../lib/xy/midiImporter";
  import type { XYProjectViewModel } from "../lib/xy/projectViewModel";
  import MidiTrackSelector from "./MidiTrackSelector.svelte";

  export let project: XYProjectViewModel;
  export let importSummary: MidiImportSummary | null;
  export let projectFileName: string;
  export let counts: { errors: number; warnings: number; info: number };
  export let onReplaceMidi: () => void;
  export let onCreateProject: () => void;
  export let onMidiTrackSelectionChange: (
    trackIds: string[],
  ) => void = () => {};
  export let midiSelectionUpdating = false;

  $: trackSelection = importSummary?.trackSelection ?? null;
  $: showTrackSelection =
    !!trackSelection &&
    (trackSelection.isSelectionRecommended ||
      trackSelection.tracks.length > trackSelection.maxInstrumentTracks);
  $: displayedTrackCount = trackSelection
    ? trackSelection.selectedTrackIds.length
    : (importSummary?.activeTracks.length ?? 0);
</script>

<section
  class="project-ready"
  class:wide={showTrackSelection}
  aria-label="MIDI project ready to create"
>
  <p class="workflow-kicker">MIDI imported</p>
  <h1>{projectFileName || "project.xy"}</h1>
  <p class="project-ready-copy">
    Scenes are arranged in sequence and ready to write as an OP–XY project.
  </p>

  {#if showTrackSelection && trackSelection}
    <MidiTrackSelector
      {project}
      selection={trackSelection}
      selectionUpdating={midiSelectionUpdating}
      onSelectionChange={onMidiTrackSelectionChange}
    />
  {/if}

  <dl class="import-details">
    <div>
      <dt>scenes</dt>
      <dd>
        {importSummary?.scenes ?? project.songs[0]?.sceneChain.length ?? 0}
      </dd>
    </div>
    <div>
      <dt>tracks</dt>
      <dd>{displayedTrackCount}</dd>
    </div>
    <div>
      <dt>tempo</dt>
      <dd>{project.tempoBpm.toFixed(1)} bpm</dd>
    </div>
    <div>
      <dt>notes</dt>
      <dd>{importSummary?.importedNotes ?? 0}</dd>
    </div>
  </dl>

  {#if counts.errors > 0 || counts.warnings > 0}
    <p class="project-validation" class:error={counts.errors > 0}>
      {counts.errors > 0
        ? `${counts.errors} validation error${counts.errors === 1 ? "" : "s"}`
        : `${counts.warnings} validation warning${counts.warnings === 1 ? "" : "s"}`}
    </p>
  {/if}

  <div class="project-ready-actions">
    <button type="button" on:click={onReplaceMidi}>replace MIDI</button>
    <button
      type="button"
      class="primary"
      disabled={midiSelectionUpdating}
      on:click={onCreateProject}>create .xy project</button
    >
  </div>
</section>

<style>
  .project-ready {
    width: min(720px, 100%);
    margin: auto;
    padding: clamp(36px, 10vh, 112px) clamp(20px, 5vw, 48px);
  }

  .project-ready.wide {
    width: min(1280px, 100%);
    padding-top: clamp(26px, 5vh, 54px);
  }

  .workflow-kicker {
    margin: 0 0 10px;
    color: var(--xy-text-muted);
    font-size: 11px;
    text-transform: uppercase;
  }

  .project-ready h1 {
    margin: 0;
    overflow-wrap: anywhere;
    font-size: clamp(32px, 7vw, 68px);
    font-weight: 500;
    letter-spacing: -0.06em;
    line-height: 0.95;
  }

  .project-ready-copy {
    max-width: 500px;
    margin: 22px 0 36px;
    color: var(--xy-text-muted);
    font-size: 16px;
    line-height: 1.5;
  }

  .import-details {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    margin: 0 0 28px;
    border-top: 1px solid var(--xy-line);
    border-bottom: 1px solid var(--xy-line);
  }

  .import-details div {
    min-width: 0;
    padding: 14px 10px 14px 0;
  }

  .import-details div + div {
    padding-left: 12px;
    border-left: 1px solid var(--xy-line);
  }

  .import-details dt {
    color: var(--xy-text-dim);
    font-size: 10px;
    text-transform: uppercase;
  }

  .import-details dd {
    margin: 5px 0 0;
    font-size: 17px;
    font-variant-numeric: tabular-nums;
  }

  .project-validation {
    margin: 0 0 20px;
    color: var(--xy-yellow-warn);
    font-size: 12px;
    text-transform: uppercase;
  }

  .project-validation.error {
    color: var(--xy-red-led);
  }

  .project-ready-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  @media (max-width: 620px) {
    .import-details {
      grid-template-columns: repeat(2, 1fr);
    }

    .import-details div:nth-child(3) {
      border-left: 0;
      border-top: 1px solid var(--xy-line);
    }

    .import-details div:nth-child(4) {
      border-top: 1px solid var(--xy-line);
    }
  }
</style>
