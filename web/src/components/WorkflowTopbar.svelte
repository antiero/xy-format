<script lang="ts">
  import type { MidiImportSummary } from "../lib/xy/midiImporter";
  import type { XYProjectViewModel } from "../lib/xy/projectViewModel";
  import ProjectTempoControl from "./ProjectTempoControl.svelte";

  type ValidationCounts = {
    errors: number;
    warnings: number;
    info: number;
  };

  type SummaryItem = {
    label: string;
    value: string;
  };

  export let project: XYProjectViewModel;
  export let projectCreated = false;
  export let projectFileName = "";
  export let importSummary: MidiImportSummary | null = null;
  export let counts: ValidationCounts = { errors: 0, warnings: 0, info: 0 };
  export let midiSelectionUpdating = false;
  export let onProjectNameCommit: () => void = () => {};
  export let onDownloadProject: () => void | Promise<void> = () => {};
  export let onTempoChange: (tempoBpm: number) => void = () => {};
  export let onRefineMidi: (() => void) | null = null;
  export let onReplaceMidi: () => void = () => {};
  export let onBurnMidiToSong: () => void | Promise<void> = () => {};

  $: trackSelection = importSummary?.trackSelection ?? null;
  $: selectedTrackCount = trackSelection
    ? trackSelection.selectedTrackIds.length
    : (importSummary?.activeTracks.length ?? 0);
  $: canBurnMidi =
    !trackSelection ||
    (trackSelection.selectedTrackIds.length > 0 &&
      trackSelection.selectedTrackIds.length <=
        trackSelection.maxInstrumentTracks &&
      trackSelection.selectedBankCount <= trackSelection.maxInstrumentTracks);
  $: midiSummaryItems = [
    {
      label: "tracks",
      value: trackSelection
        ? `${selectedTrackCount}/${trackSelection.maxInstrumentTracks} tracks`
        : `${selectedTrackCount} tracks`,
    },
    ...(trackSelection
      ? [
          {
            label: "banks",
            value: `${trackSelection.selectedBankCount}/${trackSelection.maxInstrumentTracks} banks`,
          },
        ]
      : []),
    { label: "notes", value: `${importSummary?.importedNotes ?? 0} notes` },
  ] satisfies SummaryItem[];
  $: validationText =
    counts.errors > 0
      ? `${counts.errors} error${counts.errors === 1 ? "" : "s"}`
      : counts.warnings > 0
        ? `${counts.warnings} warning${counts.warnings === 1 ? "" : "s"}`
        : "";
</script>

<header class="workflow-topbar" class:midi-editor={!projectCreated}>
  <a class="workflow-brand" href="/" aria-label="XY Buddy home">xy buddy</a>

  <div class="workflow-context">
    <label class="project-name-control">
      <input
        type="text"
        bind:value={projectFileName}
        aria-label="Project filename"
        on:change={onProjectNameCommit}
        on:blur={onProjectNameCommit}
      />
    </label>

    {#if !projectCreated}
      <div class="workflow-summary" aria-label="MIDI import summary">
        {#each midiSummaryItems as item}
          <span title={item.label}>{item.value}</span>
        {/each}
        <ProjectTempoControl tempoBpm={project.tempoBpm} {onTempoChange} />
        {#if validationText}
          <span
            class:error={counts.errors > 0}
            class:warn={counts.errors === 0}
            title="validation"
          >
            {validationText}
          </span>
        {/if}
      </div>
    {/if}
  </div>

  <div class="workflow-actions">
    {#if projectCreated}
      <button
        type="button"
        aria-label="Export this OP-XY project as a .xy file"
        title="Download .xy in the browser, or send the ready project to the Mac app"
        on:click={onDownloadProject}>export .xy</button
      >
      {#if onRefineMidi}
        <button
          type="button"
          aria-label="Refine the imported MIDI"
          title="Return to track and range selection before creating the OP-XY project"
          on:click={onRefineMidi}>Refine MIDI</button
        >
      {/if}
      <button
        type="button"
        aria-label="Choose a MIDI file or OP-XY .xy project"
        title="Open a MIDI file or OP-XY .xy project"
        on:click={onReplaceMidi}>import .mid / .xy</button
      >
    {:else}
      <button
        type="button"
        aria-label="Choose a different MIDI file or OP-XY .xy project"
        title="Choose a different MIDI file or OP-XY .xy project"
        on:click={onReplaceMidi}>replace MIDI</button
      >
      <button
        type="button"
        class="primary"
        aria-label="Create an OP-XY project from the selected MIDI"
        title="Create an OP-XY .xy project from the selected MIDI tracks"
        disabled={midiSelectionUpdating || !canBurnMidi}
        on:click={onBurnMidiToSong}>create OP-XY project</button
      >
    {/if}
  </div>
</header>

<style>
  .workflow-topbar {
    position: sticky;
    top: 0;
    z-index: 30;
    display: grid;
    min-height: 58px;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 14px;
    padding: 9px clamp(14px, 3vw, 30px);
    border-bottom: 1px solid var(--xy-line);
    background: rgba(5, 5, 5, 0.96);
    backdrop-filter: blur(14px);
  }

  .workflow-brand {
    color: var(--xy-text);
    font-size: 12px;
    font-weight: 760;
    text-decoration: none;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .workflow-context,
  .workflow-actions,
  .workflow-summary {
    display: flex;
    align-items: center;
    min-width: 0;
  }

  .workflow-context {
    gap: 12px;
  }

  .workflow-actions {
    justify-content: flex-end;
    gap: 8px;
  }

  .workflow-summary {
    gap: 6px;
    flex-wrap: wrap;
  }

  .workflow-summary span {
    border: 1px solid #313131;
    background: #0a0a0a;
    color: var(--xy-text-muted);
    padding: 6px 8px;
    font-size: 10px;
    font-variant-numeric: tabular-nums;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .workflow-summary span.error {
    color: var(--xy-red-led);
  }

  .workflow-summary span.warn {
    color: var(--xy-yellow-warn);
  }

  .project-name-control {
    display: block;
    min-width: 0;
  }

  .project-name-control input {
    min-width: 0;
    width: min(250px, 24vw);
  }

  @media (max-width: 980px) {
    .workflow-topbar {
      grid-template-columns: auto minmax(0, 1fr);
    }

    .workflow-actions {
      grid-column: 1 / -1;
      justify-content: flex-start;
    }

    .workflow-context {
      justify-content: flex-end;
    }
  }

  @media (max-width: 620px) {
    .workflow-topbar {
      grid-template-columns: 1fr;
      align-items: stretch;
      gap: 9px;
      padding: 10px 12px;
    }

    .workflow-context {
      align-items: stretch;
      flex-direction: column;
      gap: 8px;
    }

    .workflow-actions {
      align-items: stretch;
      flex-wrap: wrap;
    }

    .workflow-actions button {
      flex: 1 1 132px;
    }

    .project-name-control input {
      width: 100%;
    }
  }
</style>
