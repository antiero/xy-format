<script lang="ts">
  import type { XYProjectCompatibilityAssessment } from "../lib/xy/projectCompatibility";

  export let fileName: string;
  export let originalBytes: Uint8Array;
  export let assessment: XYProjectCompatibilityAssessment;
  export let onClose: () => void = () => {};

  function saveOriginal() {
    const blob = new Blob([originalBytes as BlobPart], {
      type: "application/octet-stream",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }
</script>

<section class="readonly-project" aria-labelledby="readonly-project-title">
  <span class="status-light" aria-hidden="true"></span>
  <p class="eyebrow">read only</p>
  <h1 id="readonly-project-title">{fileName}</h1>
  <p class="message">
    This project uses a firmware layout XY Buddy has not yet verified. Its
    original bytes are preserved; editing and device transfer are disabled.
  </p>
  <div class="actions">
    <button
      type="button"
      on:click={saveOriginal}
      title="Save an unchanged copy of the original project"
      aria-label="Save unchanged original OP-XY project">save original</button
    >
    <button
      type="button"
      class="quiet"
      on:click={onClose}
      title="Return to the project launcher"
      aria-label="Close read-only project">close</button
    >
  </div>
  <p class="fingerprint" title={`Layout ${assessment.layoutFingerprint}`}>
    firmware layout {assessment.headerVersion}
  </p>
</section>

<style>
  .readonly-project {
    width: min(560px, calc(100% - 32px));
    margin: auto;
    padding: 54px clamp(24px, 6vw, 56px);
    border: 1px solid var(--xy-line);
    background: #0b0b0b;
    text-align: center;
  }

  .status-light {
    display: inline-block;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--xy-yellow-warn);
    box-shadow: 0 0 12px rgba(244, 211, 94, 0.38);
  }

  .eyebrow,
  .fingerprint {
    color: var(--xy-text-dim);
    font-size: 10px;
    text-transform: uppercase;
  }

  h1 {
    margin: 10px 0 0;
    font-size: clamp(22px, 4vw, 34px);
    font-weight: 620;
    overflow-wrap: anywhere;
  }

  .message {
    max-width: 430px;
    margin: 18px auto 0;
    color: var(--xy-text-muted);
    font-size: 13px;
    line-height: 1.6;
  }

  .actions {
    display: flex;
    justify-content: center;
    gap: 10px;
    margin-top: 28px;
  }

  .quiet {
    color: var(--xy-text-muted);
    background: transparent;
  }

  .fingerprint {
    margin: 24px 0 0;
    font-variant-numeric: tabular-nums;
  }
</style>
