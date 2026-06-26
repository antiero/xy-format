<script lang="ts">
  import OpXyHardwareLauncher from "./components/OpXyHardwareLauncher.svelte";
  import SongModeWorkspace from "./components/SongModeWorkspace.svelte";
  import {
    announceDisplayMessage,
    currentTickStore,
    displayMessageStore,
    isPlayingStore,
    projectStore,
  } from "./stores/project";
  import { editedFileName, exportXYProject } from "./lib/xy/projectExporter";
  import { loadXYFile } from "./lib/xy/projectLoader";
  import {
    loadMidiFileAsNewProject,
    type MidiImportSummary,
  } from "./lib/xy/midiImporter";
  import { validationCounts } from "./lib/xy/validation";

  let xyFileInput: HTMLInputElement;
  let midiFileInput: HTMLInputElement;
  let loadError = "";
  let importSummary: MidiImportSummary | null = null;
  let dragging = false;
  let projectCreated = false;
  let importFileName = "";

  $: counts = $projectStore
    ? validationCounts($projectStore.validation)
    : { errors: 0, warnings: 0, info: 0 };

  async function openXYFile(file: File) {
    loadError = "";
    importSummary = null;
    try {
      const project = await loadXYFile(file);
      projectStore.set(project);
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
    announceDisplayMessage(`IMPORT ${file.name}`, "neutral");
    try {
      const result = await loadMidiFileAsNewProject(file);
      projectStore.set(result.project);
      importSummary = result.summary;
      importFileName = file.name;
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

  async function createXYProject() {
    const project = $projectStore;
    if (!project) return;
    if (
      counts.errors > 0 &&
      !window.confirm(
        `Create this project with ${counts.errors} validation error(s)?`,
      )
    ) {
      announceDisplayMessage("PROJECT CANCELLED", "warn");
      return;
    }
    announceDisplayMessage("CREATING PROJECT", "neutral");
    const blob = await exportXYProject(project);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = editedFileName(project.fileName);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    projectCreated = true;
    currentTickStore.set(0);
    announceDisplayMessage("PROJECT READY", "ok");
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
      <a class="workflow-brand" href="/" aria-label="XY Project Lab home">
        xy project lab
      </a>
      <button type="button" on:click={() => midiFileInput.click()}
        >import MIDI</button
      >
    </header>

    {#if projectCreated}
      <SongModeWorkspace project={$projectStore} />
    {:else}
      <section class="project-ready" aria-label="MIDI project ready to create">
        <p class="workflow-kicker">MIDI imported</p>
        <h1>{importFileName || "untitled MIDI"}</h1>
        <p class="project-ready-copy">
          Scenes are arranged in sequence and ready to write as an OP–XY
          project.
        </p>

        <dl class="import-details">
          <div>
            <dt>scenes</dt>
            <dd>
              {importSummary?.scenes ??
                $projectStore.songs[0]?.sceneChain.length ??
                0}
            </dd>
          </div>
          <div>
            <dt>tracks</dt>
            <dd>{importSummary?.activeTracks.length ?? 0}</dd>
          </div>
          <div>
            <dt>tempo</dt>
            <dd>{$projectStore.tempoBpm.toFixed(1)} bpm</dd>
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
          <button type="button" on:click={() => midiFileInput.click()}
            >replace MIDI</button
          >
          <button type="button" class="primary" on:click={createXYProject}
            >create .xy project</button
          >
        </div>
      </section>
    {/if}
  {:else}
    <section class="launch-surface" aria-label="OP-XY project launcher">
      <div class="launch-brand" aria-label="XY Project Lab">
        <span>xy project lab</span>
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

  .project-ready {
    width: min(720px, 100%);
    margin: auto;
    padding: clamp(36px, 10vh, 112px) clamp(20px, 5vw, 48px);
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

  .project-ready-actions,
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

    .launch-actions {
      right: 6vw;
      bottom: 70px;
    }
  }
</style>
