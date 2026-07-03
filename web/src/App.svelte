<script lang="ts">
  import OpXyHardwareLauncher from "./components/OpXyHardwareLauncher.svelte";
  import ProjectReadyPanel from "./components/ProjectReadyPanel.svelte";
  import CreatedProjectWorkspace from "./components/CreatedProjectWorkspace.svelte";
  import WorkflowTopbar from "./components/WorkflowTopbar.svelte";
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
    type MidiImportOptions,
    type MidiImportSummary,
  } from "./lib/xy/midiImporter";
  import { midiImportNeedsEditor } from "./lib/xy/midiImportWorkflow";
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
  type LaunchImportState = "idle" | "processing";

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
  let midiImportOptions: MidiImportOptions = {};
  let midiSelectionUpdating = false;
  let launchImportState: LaunchImportState = "idle";

  const LAUNCH_IMPORT_THEATRE_MS = 920;

  $: counts = $projectStore
    ? validationCounts($projectStore.validation)
    : { errors: 0, warnings: 0, info: 0 };

  function delay(milliseconds: number): Promise<void> {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
  }

  async function openXYFile(file: File) {
    loadError = "";
    importSummary = null;
    readyExport = null;
    importedMidiFile = null;
    midiImportOptions = {};
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
    midiImportOptions = {};
    midiSelectionUpdating = false;
    announceDisplayMessage(`IMPORT ${file.name}`, "neutral");
    try {
      const result = await loadMidiFileAsNewProject(file);
      projectStore.set(result.project);
      importSummary = result.summary;
      importedMidiFile = file;
      midiImportOptions = {
        bpmOverride: result.summary.bpm,
        selectedTrackIds: result.summary.trackSelection?.selectedTrackIds,
        rangeStart16ths: result.summary.rangeStart16ths,
        rangeEnd16ths: result.summary.rangeEnd16ths,
      };
      importFileName = file.name;
      projectFileName = normalizeXYFileName(result.project.fileName);
      projectCreated = false;
      currentTickStore.set(0);
      isPlayingStore.set(false);
      if (midiImportNeedsEditor(result.summary)) {
        announceDisplayMessage(
          `MIDI ${result.summary.importedNotes} NOTES`,
          "ok",
        );
      } else {
        await burnMidiToSong();
      }
    } catch (error) {
      console.error(error);
      loadError =
        error instanceof Error
          ? error.message
          : "Could not import this MIDI file.";
      announceDisplayMessage("IMPORT FAILED", "error");
    }
  }

  async function updateMidiTrackSelection(options: MidiImportOptions) {
    if (!importedMidiFile) return;

    loadError = "";
    readyExport = null;
    midiSelectionUpdating = true;
    isPlayingStore.set(false);
    currentTickStore.set(0);
    announceDisplayMessage(
      options.fitToCapacity ? "FITTING MIDI RANGE" : "UPDATING MIDI",
      "neutral",
    );

    try {
      const nextOptions = {
        ...midiImportOptions,
        ...options,
      };
      const result = await loadMidiFileAsNewProject(
        importedMidiFile,
        nextOptions,
      );
      projectStore.set(result.project);
      importSummary = result.summary;
      midiImportOptions = {
        bpmOverride: result.summary.bpm,
        selectedTrackIds: result.summary.trackSelection?.selectedTrackIds,
        rangeStart16ths: result.summary.rangeStart16ths,
        rangeEnd16ths: result.summary.rangeEnd16ths,
      };
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

  async function handleSelectedFile(file: File) {
    const isLaunchImport = !$projectStore;
    if (isLaunchImport) {
      launchImportState = "processing";
      announceDisplayMessage("READING FILE", "neutral");
      await delay(LAUNCH_IMPORT_THEATRE_MS);
    }

    if (file.name.toLowerCase().endsWith(".xy")) {
      await openXYFile(file);
    } else if (file.name.toLowerCase().includes(".mid")) {
      await importMidiFile(file);
    } else {
      loadError = "Please select a valid .xy or .mid file.";
      announceDisplayMessage("INVALID FILE", "error");
    }
    if (!$projectStore) launchImportState = "idle";
  }

  async function handleFileUpload(event: Event) {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (file) await handleSelectedFile(file);
    target.value = "";
  }

  async function handleDrop(event: DragEvent) {
    event.preventDefault();
    dragging = false;
    const file = event.dataTransfer?.files?.[0];
    if (file) await handleSelectedFile(file);
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
    const currentCounts = validationCounts(project.validation);
    if (
      currentCounts.errors > 0 &&
      !window.confirm(
        `Create this project with ${currentCounts.errors} validation error(s)?`,
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

  async function burnMidiToSong() {
    const exportData = await createReadyExport(false, false);
    if (exportData) {
      announceDisplayMessage("SONG READY", "ok");
    }
  }

  function returnToMidiEditor() {
    if (!importedMidiFile || !importSummary) return;
    readyExport = null;
    projectCreated = false;
    currentTickStore.set(0);
    isPlayingStore.set(false);
    announceDisplayMessage("MIDI EDITOR", "neutral");
  }

  function rememberTempoOverride(tempoBpm: number) {
    readyExport = null;
    if (importedMidiFile) {
      midiImportOptions = { ...midiImportOptions, bpmOverride: tempoBpm };
      if (importSummary) importSummary = { ...importSummary, bpm: tempoBpm };
    }
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
    accept=".xy,.mid,.midi"
    tabindex="-1"
    bind:this={xyFileInput}
    on:change={handleFileUpload}
    class="visually-hidden"
  />
  <input
    type="file"
    accept=".xy,.mid,.midi"
    tabindex="-1"
    bind:this={midiFileInput}
    on:change={handleFileUpload}
    class="visually-hidden"
  />

  {#if $projectStore}
    <WorkflowTopbar
      project={$projectStore}
      {projectCreated}
      bind:projectFileName
      {importSummary}
      {counts}
      {midiSelectionUpdating}
      onProjectNameCommit={() => commitProjectFileName()}
      onDownloadProject={downloadXYProject}
      onTempoChange={rememberTempoOverride}
      onRefineMidi={importedMidiFile && importSummary?.trackSelection
        ? returnToMidiEditor
        : null}
      onReplaceMidi={() => midiFileInput.click()}
      onBurnMidiToSong={burnMidiToSong}
    />

    {#if projectCreated}
      <CreatedProjectWorkspace
        project={$projectStore}
        onTempoChange={rememberTempoOverride}
      />
    {:else}
      <ProjectReadyPanel
        project={$projectStore}
        {importSummary}
        {midiSelectionUpdating}
        onMidiTrackSelectionChange={updateMidiTrackSelection}
      />
    {/if}
  {:else}
    <section class="launch-surface" aria-label="OP-XY project launcher">
      <div class="launch-brand" aria-label="XY buddy">
        <span>xy buddy</span>
        <span>unofficial op-xy project utility</span>
      </div>

      <OpXyHardwareLauncher
        tempo={120}
        message={$displayMessageStore}
        {dragging}
        importState={launchImportState}
        onOpenXY={() => xyFileInput.click()}
        onImportMidi={() => midiFileInput.click()}
      />

      {#if loadError}
        <p class="load-error launch-error">{loadError}</p>
      {/if}

      <p class="disclaimer">
        app by <a href="https://github.com/antiero/xy-format" target="_blank"
          >antiero (5of12)</a
        >. not affiliated with teenage engineering. <br />made possible by
        reverse engineering efforts of
        <a href="https://github.com/kmorrill/xy-format" target="_blank"
          >kmorrill</a
        >.
        <span class="firmware-footnote">
          supports op-xy firmware 1.1.15 or later.
        </span>
      </p>
    </section>
  {/if}
</main>
