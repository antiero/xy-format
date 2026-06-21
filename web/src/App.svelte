<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import ProjectWorkspace from "./components/ProjectWorkspace.svelte";
  import DawWorkspace from "./components/DawWorkspace.svelte";
  import PatternWorkspace from "./components/PatternWorkspace.svelte";
  import ArrangeWorkspace from "./components/ArrangeWorkspace.svelte";
  import InspectWorkspace from "./components/InspectWorkspace.svelte";
  import {
    activeModeStore,
    projectStore,
    type WorkspaceMode,
  } from "./stores/project";
  import { editedFileName, exportXYProject } from "./lib/xy/projectExporter";
  import { loadXYFile } from "./lib/xy/projectLoader";
  import {
    loadMidiFileAsNewProject,
    type MidiImportSummary,
  } from "./lib/xy/midiImporter";
  import { projectSummary } from "./lib/xy/projectViewModel";
  import { validationCounts } from "./lib/xy/validation";

  let xyFileInput: HTMLInputElement;
  let midiFileInput: HTMLInputElement;
  let loadError = "";
  let importSummary: MidiImportSummary | null = null;
  let midiBpmOverride = "";
  let dragging = false;

  const modes: { id: WorkspaceMode; label: string }[] = [
    { id: "project", label: "Project" },
    { id: "daw", label: "DAW" },
    { id: "pattern", label: "Pattern" },
    { id: "arrange", label: "Arrange" },
    { id: "inspect", label: "Inspect" },
  ];

  $: counts = $projectStore
    ? validationCounts($projectStore.validation)
    : { errors: 0, warnings: 0, info: 0 };

  function midiImportLabel(summary: MidiImportSummary): string {
    const tracks = summary.activeTracks.map((track) => `T${track}`).join("/");
    return `MIDI ${summary.patterns}p ${summary.totalBars}b ${summary.importedNotes}n ${tracks}`;
  }

  function parsedBpmOverride(): number | undefined {
    const bpm = Number(midiBpmOverride);
    if (!Number.isFinite(bpm) || bpm <= 0) return undefined;
    return bpm;
  }

  async function openXYFile(file: File) {
    loadError = "";
    importSummary = null;
    try {
      const project = await loadXYFile(file);
      projectStore.set(project);
      activeModeStore.set("daw");
    } catch (error) {
      console.error(error);
      loadError =
        error instanceof Error
          ? error.message
          : "Could not parse this .xy file.";
    }
  }

  async function importMidiFile(file: File) {
    loadError = "";
    importSummary = null;
    try {
      const result = await loadMidiFileAsNewProject(file, {
        bpmOverride: parsedBpmOverride(),
      });
      projectStore.set(result.project);
      importSummary = result.summary;
      activeModeStore.set("daw");
    } catch (error) {
      console.error(error);
      loadError =
        error instanceof Error
          ? error.message
          : "Could not import this MIDI file.";
    }
  }

  async function openFile(file: File) {
    const name = file.name.toLowerCase();
    if (name.endsWith(".mid") || name.endsWith(".midi")) {
      await importMidiFile(file);
      return;
    }
    await openXYFile(file);
  }

  async function handleXYFileUpload(event: Event) {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (file) await openXYFile(file);
    target.value = "";
  }

  async function handleMidiFileUpload(event: Event) {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (file) await importMidiFile(file);
    target.value = "";
  }

  async function handleDrop(event: DragEvent) {
    event.preventDefault();
    dragging = false;
    const file = event.dataTransfer?.files?.[0];
    if (file) await openFile(file);
  }

  async function handleDownload() {
    const project = $projectStore;
    if (!project) return;
    if (
      counts.errors > 0 &&
      !window.confirm(`Export with ${counts.errors} validation error(s)?`)
    ) {
      return;
    }
    const blob = await exportXYProject(project);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = editedFileName(project.fileName);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function handleKeydown(event: KeyboardEvent) {
    const project = $projectStore;
    if (!project) return;
    const key = event.key.toLowerCase();
    if ((event.metaKey || event.ctrlKey) && key === "s") {
      event.preventDefault();
      void handleDownload();
    } else if (key === "p" && !event.metaKey && !event.ctrlKey) {
      activeModeStore.set("pattern");
    } else if (key === "d" && !event.metaKey && !event.ctrlKey) {
      activeModeStore.set("daw");
    } else if (key === "a" && !event.metaKey && !event.ctrlKey) {
      activeModeStore.set("arrange");
    }
  }

  onMount(() => {
    window.addEventListener("keydown", handleKeydown);
  });

  onDestroy(() => {
    window.removeEventListener("keydown", handleKeydown);
  });
</script>

<main
  class="app-shell"
  class:dragging
  on:dragover|preventDefault={() => (dragging = true)}
  on:dragleave={() => (dragging = false)}
  on:drop={handleDrop}
>
  <input
    type="file"
    accept=".xy"
    bind:this={xyFileInput}
    on:change={handleXYFileUpload}
    class="visually-hidden"
  />
  <input
    type="file"
    accept=".mid,.midi"
    bind:this={midiFileInput}
    on:change={handleMidiFileUpload}
    class="visually-hidden"
  />

  <header class="topbar">
    <div class="brand-lockup">
      <span class="brand-led"></span>
      <div>
        <h1>XY Project Lab</h1>
        <p>unofficial OP-XY project-file utility</p>
      </div>
    </div>

    {#if $projectStore}
      <div class="project-status">
        <span>{$projectStore.fileName}</span>
        <span>{$projectStore.modified ? "modified" : "clean"}</span>
        {#if importSummary}
          <span>{midiImportLabel(importSummary)}</span>
        {/if}
        <span
          class:error={counts.errors > 0}
          class:warn={counts.errors === 0 && counts.warnings > 0}
        >
          {counts.errors}e · {counts.warnings}w
        </span>
      </div>
    {/if}

    <div class="toolbar-actions">
      <button type="button" on:click={() => xyFileInput.click()}
        >open .xy</button
      >
      <input
        class="tempo-input"
        type="number"
        min="10"
        max="300"
        step="0.1"
        placeholder="BPM"
        aria-label="MIDI BPM override"
        bind:value={midiBpmOverride}
      />
      <button type="button" on:click={() => midiFileInput.click()}
        >import MIDI</button
      >
      <button
        type="button"
        disabled={!$projectStore}
        class="primary"
        on:click={handleDownload}>export</button
      >
    </div>
  </header>

  {#if $projectStore}
    <nav class="modebar" aria-label="Workspace mode">
      {#each modes as mode}
        <button
          type="button"
          class:active={$activeModeStore === mode.id}
          on:click={() => activeModeStore.set(mode.id)}
        >
          {mode.label}
        </button>
      {/each}
      <span>{projectSummary($projectStore)}</span>
    </nav>

    <div class="workspace-frame">
      {#if $activeModeStore === "project"}
        <ProjectWorkspace project={$projectStore} />
      {:else if $activeModeStore === "daw"}
        <DawWorkspace project={$projectStore} />
      {:else if $activeModeStore === "pattern"}
        <PatternWorkspace project={$projectStore} />
      {:else if $activeModeStore === "arrange"}
        <ArrangeWorkspace project={$projectStore} />
      {:else}
        <InspectWorkspace project={$projectStore} />
      {/if}
    </div>
  {:else}
    <section class="launch-surface">
      <div class="launch-copy">
        <p class="eyebrow">Local project editor</p>
        <h2>XY Project Lab</h2>
        <p>inspect, arrange and export OP-XY project files</p>
        <div class="launch-actions">
          <input
            class="tempo-input"
            type="number"
            min="10"
            max="300"
            step="0.1"
            placeholder="BPM"
            aria-label="MIDI BPM override"
            bind:value={midiBpmOverride}
          />
          <button
            type="button"
            class="primary"
            on:click={() => midiFileInput.click()}>import MIDI</button
          >
          <button type="button" on:click={() => xyFileInput.click()}
            >open .xy project</button
          >
        </div>
        {#if loadError}
          <p class="load-error">{loadError}</p>
        {/if}
      </div>
      <div class="device-plane" aria-hidden="true">
        <div class="screen-line"></div>
        <div class="device-grid">
          {#each Array(64) as _, i}
            <span class:red={i % 17 === 0}></span>
          {/each}
        </div>
      </div>
      <p class="disclaimer">
        Unofficial project-file utility for OP-XY. Teenage Engineering and OP-XY
        are trademarks of their respective owners.
      </p>
    </section>
  {/if}
</main>
