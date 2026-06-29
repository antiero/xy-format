<script lang="ts">
  import OpXyHardwareLauncher from "./components/OpXyHardwareLauncher.svelte";
  import ProjectReadyPanel from "./components/ProjectReadyPanel.svelte";
  import SongModeWorkspace from "./components/SongModeWorkspace.svelte";
  import {
    announceDisplayMessage,
    currentTickStore,
    displayMessageStore,
    isPlayingStore,
    projectStore,
    setProjectFileName,
  } from "./stores/project";
  import {
    exportXYProjectBytes,
    normalizeXYFileName,
  } from "./lib/xy/projectExporter";
  import { loadXYFile } from "./lib/xy/projectLoader";
  import {
    loadMidiFileAsNewProject,
    type MidiImportSummary,
  } from "./lib/xy/midiImporter";
  import { validationCounts } from "./lib/xy/validation";
  import {
    bytesToBase64,
    publishNativeExport,
    type XYBuddyNativeExportPayload,
  } from "./lib/nativeBridge";

  type ReadyProjectExport = {
    filename: string;
    bytes: Uint8Array;
    sourceMidiFilename: string | null;
  };

  let xyFileInput: HTMLInputElement;
  let midiFileInput: HTMLInputElement;
  let loadError = "";
  let importSummary: MidiImportSummary | null = null;
  let dragging = false;
  let projectCreated = false;
  let importFileName = "";
  let projectFileName = "";
  let readyExport: ReadyProjectExport | null = null;
  let importedMidiFile: File | null = null;
  let midiSelectionUpdating = false;

  $: counts = $projectStore
    ? validationCounts($projectStore.validation)
    : { errors: 0, warnings: 0, info: 0 };

  async function openXYFile(file: File) {
    loadError = "";
    importSummary = null;
    readyExport = null;
    importedMidiFile = null;
    midiSelectionUpdating = false;
    try {
      const project = await loadXYFile(file);
      projectStore.set(project);
      projectFileName = normalizeXYFileName(project.fileName);
      projectCreated = true;
      importFileName = file.name;
      currentTickStore.set(0);
      announceDisplayMessage(`LOADED ${file.name}`, "ok");
    } catch (error) {
      console.error(error);
      loadError =
        error instanceof Error
          ? error.message
          : "Could not parse this .xy file.";
      announceDisplayMessage("OPEN FAILED", "error");
    }
  }

  async function importMidiFile(file: File) {
    loadError = "";
    importSummary = null;
    readyExport = null;
    importedMidiFile = null;
    midiSelectionUpdating = false;
    announceDisplayMessage(`IMPORT ${file.name}`, "neutral");
    try {
      const result = await loadMidiFileAsNewProject(file);
      projectStore.set(result.project);
      importSummary = result.summary;
      importedMidiFile = file;
      importFileName = file.name;
      projectFileName = normalizeXYFileName(result.project.fileName);
      projectCreated = false;
      currentTickStore.set(0);
      isPlayingStore.set(false);
      announceDisplayMessage(
        `MIDI ${result.summary.importedNotes} NOTES`,
        "ok",
      );
    } catch (error) {
      console.error(error);
      loadError =
        error instanceof Error
          ? error.message
          : "Could not import this MIDI file.";
      announceDisplayMessage("IMPORT FAILED", "error");
    }
  }

  async function updateMidiTrackSelection(trackIds: string[]) {
    if (!importedMidiFile) return;

    loadError = "";
    readyExport = null;
    midiSelectionUpdating = true;
    isPlayingStore.set(false);
    currentTickStore.set(0);
    announceDisplayMessage("UPDATING TRACKS", "neutral");

    try {
      const result = await loadMidiFileAsNewProject(importedMidiFile, {
        selectedTrackIds: trackIds,
      });
      projectStore.set(result.project);
      importSummary = result.summary;
      projectFileName = normalizeXYFileName(result.project.fileName);
      projectCreated = false;
      announceDisplayMessage(
        `MIDI ${result.summary.activeTracks.length} TRACKS`,
        "ok",
      );
    } catch (error) {
      console.error(error);
      loadError =
        error instanceof Error
          ? error.message
          : "Could not rebuild this MIDI selection.";
      announceDisplayMessage("TRACK UPDATE FAILED", "error");
    } finally {
      midiSelectionUpdating = false;
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

  function commitProjectFileName(publish = true): string {
    const filename = normalizeXYFileName(
      projectFileName || $projectStore?.fileName || "",
    );
    projectFileName = filename;
    setProjectFileName(filename);
    if (readyExport && readyExport.filename !== filename) {
      readyExport = { ...readyExport, filename };
      if (publish) publishReadyExport(readyExport);
    }
    return filename;
  }

  function nativeExportPayload(
    exportData: ReadyProjectExport,
  ): XYBuddyNativeExportPayload {
    return {
      filename: exportData.filename,
      base64Data: bytesToBase64(exportData.bytes),
      metadata: {
        sourceMidiFilename: exportData.sourceMidiFilename,
        generatorVersion: "xy-format web",
        xyFormatVersion: "live",
      },
      compatibilityStatus: "unknownFirmware",
    };
  }

  function publishReadyExport(exportData: ReadyProjectExport): boolean {
    return publishNativeExport(nativeExportPayload(exportData));
  }

  async function createReadyExport(
    publishToNative: boolean,
    announceReady = true,
  ): Promise<ReadyProjectExport | null> {
    const project = $projectStore;
    if (!project) return null;
    if (
      counts.errors > 0 &&
      !window.confirm(
        `Create this project with ${counts.errors} validation error(s)?`,
      )
    ) {
      announceDisplayMessage("PROJECT CANCELLED", "warn");
      return null;
    }
    announceDisplayMessage("CREATING PROJECT", "neutral");
    const filename = commitProjectFileName(false);
    const currentProject = $projectStore ?? project;
    readyExport = {
      filename,
      bytes: exportXYProjectBytes(currentProject),
      sourceMidiFilename: importFileName || null,
    };
    projectCreated = true;
    currentTickStore.set(0);
    const published = publishToNative && publishReadyExport(readyExport);
    if (announceReady) {
      announceDisplayMessage(
        published ? "READY IN MAC APP" : "PROJECT READY",
        "ok",
      );
    }
    return readyExport;
  }

  async function createXYProject() {
    await createReadyExport(true);
  }

  async function downloadXYProject() {
    const exportData = await createReadyExport(false, false);
    if (!exportData) return;

    if (publishReadyExport(exportData)) {
      announceDisplayMessage("READY IN MAC APP", "ok");
      return;
    }

    const blob = new Blob([exportData.bytes as BlobPart], {
      type: "application/octet-stream",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = exportData.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    announceDisplayMessage("DOWNLOAD STARTED", "ok");
  }
</script>

<main
  class="app-shell"
  class:launching={!$projectStore}
  class:dragging
  on:dragover|preventDefault={() => (dragging = true)}
  on:dragleave={() => (dragging = false)}
  on:drop={handleDrop}
>
  <input
    type="file"
    accept=".xy"
    tabindex="-1"
    bind:this={xyFileInput}
    on:change={handleXYFileUpload}
    class="visually-hidden"
  />
  <input
    type="file"
    accept=".mid,.midi"
    tabindex="-1"
    bind:this={midiFileInput}
    on:change={handleMidiFileUpload}
    class="visually-hidden"
  />

  {#if $projectStore}
    <header class="workflow-topbar">
      <a class="workflow-brand" href="/" aria-label="XY Buddy home">
        xy buddy
      </a>
      <div class="workflow-actions">
        <label class="project-name-control">
          <span>project name</span>
          <input
            type="text"
            bind:value={projectFileName}
            aria-label="Project filename"
            on:change={() => commitProjectFileName()}
            on:blur={() => commitProjectFileName()}
          />
        </label>
        {#if projectCreated}
          <button type="button" on:click={downloadXYProject}
            >download .xy</button
          >
        {/if}
        <button type="button" on:click={() => midiFileInput.click()}
          >import MIDI</button
        >
      </div>
    </header>

    {#if projectCreated}
      <SongModeWorkspace project={$projectStore} />
    {:else}
      <ProjectReadyPanel
        project={$projectStore}
        {importSummary}
        {projectFileName}
        {counts}
        {midiSelectionUpdating}
        onReplaceMidi={() => midiFileInput.click()}
        onCreateProject={createXYProject}
        onMidiTrackSelectionChange={updateMidiTrackSelection}
      />
    {/if}
  {:else}
    <section class="launch-surface" aria-label="OP-XY project launcher">
      <div class="launch-brand" aria-label="XY buddy">
        <span>xy buddy</span>
        <span>op-xy project utility</span>
      </div>

      <OpXyHardwareLauncher
        tempo={120}
        message={$displayMessageStore}
        {dragging}
        onOpenXY={() => xyFileInput.click()}
        onImportMidi={() => midiFileInput.click()}
      />

      <div class="launch-actions">
        <button
          type="button"
          class="primary"
          on:click={() => midiFileInput.click()}>import MIDI</button
        >
      </div>

      {#if loadError}
        <p class="load-error launch-error">{loadError}</p>
      {/if}

      <p class="disclaimer">
        Unofficial project-file utility for OP-XY. Teenage Engineering and OP-XY
        are trademarks of their respective owners.
      </p>
    </section>
  {/if}
</main>

<style>
  .workflow-topbar {
    display: flex;
    min-height: 58px;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 10px clamp(16px, 3vw, 32px);
    border-bottom: 1px solid var(--xy-line);
    background: rgba(5, 5, 5, 0.92);
  }

  .workflow-brand {
    color: var(--xy-text);
    font-size: 12px;
    font-weight: 760;
    text-decoration: none;
    text-transform: uppercase;
  }

  .workflow-actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    min-width: 0;
  }

  .project-name-control {
    display: grid;
    grid-template-columns: auto minmax(170px, 260px);
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .project-name-control span {
    color: var(--xy-text-dim);
    font-size: 10px;
    text-transform: uppercase;
  }

  .project-name-control input {
    min-width: 0;
  }

  .launch-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .launch-actions {
    position: absolute;
    z-index: 3;
    left: 6vw;
    bottom: 84px;
  }

  @media (max-width: 620px) {
    .workflow-topbar {
      align-items: flex-start;
      flex-direction: column;
    }

    .workflow-actions {
      width: 100%;
      justify-content: flex-start;
      flex-wrap: wrap;
    }

    .project-name-control {
      width: 100%;
      grid-template-columns: 1fr;
    }

    .launch-actions {
      right: 6vw;
      bottom: 70px;
    }
  }
</style>
