<script lang="ts">
  import { onDestroy } from "svelte";
  import midibulbSvg from "../assets/midibulb.svg";
  import { downloadBytes } from "../lib/download";
  import {
    exportPatternMidis,
    exportSongMidi,
    exportTrackMidis,
    midiProjectBaseName,
    type MidiExportOptions,
  } from "../lib/xy/midiExporter";
  import type { XYProjectViewModel } from "../lib/xy/projectViewModel";
  import { createZipArchive, type ZipProgress } from "../lib/zip";
  import { announceDisplayMessage } from "../stores/project";

  export let project: XYProjectViewModel;
  export let includeDisabledTracks = false;
  export let exportableNotes = 0;
  export let isPlaying = false;
  export let transportState: "idle" | "loading" | "playing" = "idle";
  export let playbackAvailable = false;
  export let onTogglePlayback: () => void | Promise<void>;
  export let onRewindPlayback: () => void;
  export let onEditMidi: (() => void) | null = null;

  type ExportOverlay = {
    title: string;
    quip: string;
    progress: number;
    detail: string;
  };

  const EXPORT_QUIPS = [
    "Summoning Kakehashi Spirit",
    "Dave Smith Approves",
    "MIDI is Great",
    "When is MIDI 2.0 coming?",
    "MIDI connects people.",
    "MIDI 4tw.",
    "Time for Program Change.",
    "MIDI does karaoke too.",
    "General MIDI, at your service.",
    "Let the music live on.",
    "MIDI. The perfect format.",
    "MIDI. Rockin' since 1983.",
    "Where would we be without MIDI?",
    "MIDI now burning to digital tape.",
    "Your MIDI will be ready shortly...",
  ];
  const MIN_FAKE_EXPORT_MS = 3000;
  const MAX_FAKE_EXPORT_MS = 5000;

  let overlay: ExportOverlay | null = null;
  let exportFrame = 0;

  $: exportOptions = { includeDisabledTracks } satisfies MidiExportOptions;
  $: exporting = overlay !== null;

  function randomQuip(): string {
    return EXPORT_QUIPS[Math.floor(Math.random() * EXPORT_QUIPS.length)];
  }

  function delay(ms: number): Promise<void> {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function nextFrame(): Promise<void> {
    return new Promise((resolve) => requestAnimationFrame(() => resolve()));
  }

  function setOverlay(progress: number, detail: string): void {
    if (!overlay) return;
    overlay = {
      ...overlay,
      progress: Math.max(overlay.progress, progress),
      detail,
    };
  }

  function fakeExportMs(): number {
    return (
      MIN_FAKE_EXPORT_MS +
      Math.random() * (MAX_FAKE_EXPORT_MS - MIN_FAKE_EXPORT_MS)
    );
  }

  function easedProgress(ratio: number): number {
    return 1 - Math.pow(1 - ratio, 3);
  }

  function cancelFakeProgress(): void {
    if (!exportFrame) return;
    cancelAnimationFrame(exportFrame);
    exportFrame = 0;
  }

  function startFakeProgress(startedAt: number, durationMs: number): void {
    cancelFakeProgress();
    const tick = () => {
      if (!overlay) return;
      const ratio = Math.min(1, (performance.now() - startedAt) / durationMs);
      const progress = 0.05 + easedProgress(ratio) * 0.88;
      setOverlay(progress, overlay.detail);
      if (ratio < 1) {
        exportFrame = requestAnimationFrame(tick);
      }
    };
    exportFrame = requestAnimationFrame(tick);
  }

  async function runExport(
    title: string,
    task: () => Promise<void>,
  ): Promise<void> {
    if (exporting) return;
    const startedAt = performance.now();
    const durationMs = fakeExportMs();
    overlay = {
      title,
      quip: randomQuip(),
      progress: 0.03,
      detail: "Preparing",
    };
    await nextFrame();
    startFakeProgress(startedAt, durationMs);
    try {
      await task();
      const remainingMs = Math.max(
        0,
        durationMs - (performance.now() - startedAt),
      );
      await delay(remainingMs);
      cancelFakeProgress();
      setOverlay(1, "Done");
      await delay(420);
    } finally {
      cancelFakeProgress();
      overlay = null;
    }
  }

  function zipProgress(progress: ZipProgress): void {
    const ratio = progress.total ? progress.current / progress.total : 1;
    setOverlay(0.18 + ratio * 0.34, progress.filename);
  }

  async function downloadZip(
    filename: string,
    files: { filename: string; bytes: Uint8Array }[],
  ): Promise<void> {
    setOverlay(0.1, `Packing ${files.length} files`);
    await delay(120);
    const zipBytes = await createZipArchive(files, zipProgress);
    setOverlay(0.62, "Starting download");
    downloadBytes(filename, zipBytes, "application/zip");
  }

  async function exportSong(): Promise<void> {
    if (exportableNotes === 0) return;
    await runExport("Export Song", async () => {
      setOverlay(0.18, "Rendering MIDI");
      const file = exportSongMidi(project, project.fileName, exportOptions);
      await delay(120);
      setOverlay(0.52, file.filename);
      downloadBytes(file.filename, file.bytes, "audio/midi");
      announceDisplayMessage("MIDI SONG EXPORTED", "ok");
    });
  }

  async function exportTracks(): Promise<void> {
    if (exportableNotes === 0) return;
    await runExport("Export Tracks", async () => {
      const files = exportTrackMidis(project, exportOptions);
      if (files.length === 0) return;
      await downloadZip(
        `${midiProjectBaseName(project.fileName)}-tracks.zip`,
        files,
      );
      announceDisplayMessage(`${files.length} MIDI TRACKS`, "ok");
    });
  }

  async function exportPatterns(): Promise<void> {
    if (exportableNotes === 0) return;
    await runExport("Export Patterns", async () => {
      const files = exportPatternMidis(
        project,
        project.fileName,
        exportOptions,
      );
      if (files.length === 0) return;
      await downloadZip(
        `${midiProjectBaseName(project.fileName)}-patterns.zip`,
        files,
      );
      announceDisplayMessage(`${files.length} MIDI PATTERNS`, "ok");
    });
  }

  onDestroy(() => {
    cancelFakeProgress();
  });
</script>

<div class="export-actions">
  <button
    type="button"
    class:active={isPlaying}
    disabled={exporting || transportState === "loading" || !playbackAvailable}
    aria-label={isPlaying ? "Stop arrangement playback" : "Play arrangement"}
    title={isPlaying ? "Stop arrangement playback" : "Play arrangement"}
    on:click={onTogglePlayback}
  >
    {isPlaying ? "Stop" : transportState === "loading" ? "Load" : "Play"}
  </button>
  <button
    type="button"
    disabled={exporting}
    aria-label="Rewind arrangement playback"
    title="Rewind arrangement playback"
    on:click={onRewindPlayback}>Rew</button
  >
  {#if onEditMidi}
    <button
      type="button"
      class="subtle"
      disabled={exporting}
      on:click={onEditMidi}>edit MIDI</button
    >
  {/if}
  <label
    class="include-disabled"
    title="Include scene-muted tracks in exported MIDI"
  >
    <input
      type="checkbox"
      bind:checked={includeDisabledTracks}
      disabled={exporting}
    />
    <span>Include Disabled Tracks</span>
  </label>
  <button
    type="button"
    disabled={exporting || exportableNotes === 0}
    title="Export the visible arrangement as one multi-track MIDI file"
    aria-label="Export song MIDI file"
    on:click={exportSong}>Export Song</button
  >
  <button
    type="button"
    disabled={exporting || exportableNotes === 0}
    title="Export one zipped MIDI file bundle for non-empty instrument tracks"
    aria-label="Export separate MIDI track files as a zip"
    on:click={exportTracks}>Export Tracks</button
  >
  <button
    type="button"
    disabled={exporting || exportableNotes === 0}
    title="Export one zipped MIDI file bundle for non-empty instrument patterns"
    aria-label="Export individual MIDI pattern files as a zip"
    on:click={exportPatterns}>Export Patterns</button
  >
</div>

{#if overlay}
  <div
    class="export-overlay"
    role="dialog"
    aria-modal="true"
    aria-labelledby="export-title"
    aria-describedby="export-quip"
  >
    <div class="export-dialog">
      <img src={midibulbSvg} alt="" aria-hidden="true" />
      <p id="export-title" class="export-title">{overlay.title}</p>
      <p id="export-quip" class="export-quip">{overlay.quip}</p>
      <div
        class="export-progress"
        role="progressbar"
        aria-label="MIDI export progress"
        aria-valuemin="0"
        aria-valuemax="100"
        aria-valuenow={Math.round(overlay.progress * 100)}
      >
        <span style={`width: ${Math.round(overlay.progress * 100)}%`}></span>
      </div>
      <p class="export-detail">{overlay.detail}</p>
    </div>
  </div>
{/if}

<style>
  .export-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .export-actions button {
    min-height: 32px;
    border-color: #33343a;
    background: #151515;
    color: #efeeec;
    box-shadow: none;
  }

  .export-actions button:hover:not(:disabled) {
    border-color: #76777d;
    background: #24242a;
  }

  .export-actions button.active {
    border-color: #f3f1ef;
    background: #f3f1ef;
    color: #050505;
  }

  .include-disabled {
    display: flex;
    align-items: center;
    gap: 7px;
    min-height: 32px;
    color: #bfc0c5;
    font-size: 11px;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .include-disabled input {
    width: 14px;
    height: 14px;
    min-height: 0;
    margin: 0;
    accent-color: #f3f1ef;
  }

  .export-overlay {
    position: fixed;
    z-index: 200;
    inset: 0;
    display: grid;
    place-items: center;
    padding: 24px;
    background: rgba(0, 0, 0, 0.72);
    backdrop-filter: blur(10px);
  }

  .export-dialog {
    width: min(380px, 100%);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    background: #050505;
    box-shadow: 0 22px 90px rgba(0, 0, 0, 0.58);
    padding: 28px 28px 24px;
    text-align: center;
  }

  .export-dialog img {
    width: 116px;
    height: auto;
    margin: 0 auto 10px;
    opacity: 0.92;
  }

  .export-title {
    margin: 0;
    color: #a7a7ac;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    text-transform: uppercase;
  }

  .export-quip {
    margin: 8px 0 20px;
    color: #f7f5f5;
    font-size: 22px;
    font-weight: 520;
    line-height: 1.14;
  }

  .export-progress {
    height: 8px;
    overflow: hidden;
    border: 1px solid #3b3b40;
    border-radius: 999px;
    background: #111;
  }

  .export-progress span {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: #f7f5f5;
    transition: width 180ms ease;
  }

  .export-detail {
    min-height: 14px;
    margin: 11px 0 0;
    color: #8e8e96;
    font-size: 11px;
    text-transform: uppercase;
  }

  @media (max-width: 760px) {
    .export-actions {
      justify-content: flex-end;
      flex-wrap: wrap;
    }

    .export-dialog {
      padding: 24px 22px 22px;
    }
  }
</style>
