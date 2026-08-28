<script lang="ts">
  export let totalSteps: number;
  export let trackScale: string;
  export let onSetSteps: (steps: number) => void = () => {};
  export let onSetScale: (scale: string) => void = () => {};
  export let onRotate: (steps: number) => void = () => {};

  const barLengths = [16, 32, 48, 64];
  const scales = ["1/2", "1", "2", "3", "4", "5", "6", "7", "8", "16"];
</script>

<section class="timing-controls" aria-label="Pattern length and scale">
  <div class="timing-section">
    <label class="field-label">
      length · steps
      <input
        type="number"
        min="1"
        max="64"
        value={totalSteps}
        on:change={(event) =>
          onSetSteps(Number((event.target as HTMLInputElement).value))}
      />
    </label>
    <div class="hardware-pad-grid" aria-label="Pattern length presets">
      {#each barLengths as steps}
        <button
          class="hardware-pad"
          type="button"
          class:active={totalSteps === steps}
          aria-label={`Set pattern length to ${steps / 16} bar${steps === 16 ? "" : "s"}`}
          title={`${steps / 16} bar${steps === 16 ? "" : "s"}`}
          on:click={() => onSetSteps(steps)}
        >
          {steps / 16}B
        </button>
      {/each}
    </div>
    <div class="rotate-row" aria-label="Rotate pattern">
      <button
        class="hardware-pad compact"
        type="button"
        title="Rotate triggers, parameter locks and components one step earlier"
        aria-label="Rotate pattern one step left"
        on:click={() => onRotate(-1)}>←</button
      >
      <button
        class="hardware-pad compact"
        type="button"
        title="Rotate triggers, parameter locks and components one step later"
        aria-label="Rotate pattern one step right"
        on:click={() => onRotate(1)}>→</button
      >
    </div>
  </div>

  <div class="timing-section">
    <span class="rail-label">scale</span>
    <div class="hardware-pad-grid" aria-label="Pattern scale">
      {#each scales as scale}
        <button
          class="hardware-pad"
          type="button"
          class:active={trackScale === scale}
          aria-label={`Set scale ${scale}`}
          title={`Set scale ${scale}`}
          on:click={() => onSetScale(scale)}
        >
          {scale}
        </button>
      {/each}
    </div>
  </div>
</section>

<style>
  .timing-controls {
    padding-bottom: 14px;
    margin-bottom: 14px;
    border-bottom: 1px solid var(--xy-line);
  }

  .timing-section + .timing-section {
    margin-top: 14px;
  }

  .hardware-pad-grid {
    display: grid;
    grid-template-columns: repeat(4, 48px);
    gap: 6px;
    justify-content: space-between;
  }

  .hardware-pad {
    position: relative;
    isolation: isolate;
    display: grid;
    width: 48px;
    min-width: 48px;
    height: 48px;
    min-height: 48px;
    padding: 0;
    place-items: center;
    overflow: hidden;
    border-color: #020202;
    border-radius: 6px;
    background: linear-gradient(180deg, #252525, #111 58%, #070707);
    color: var(--xy-text-muted);
    font-variant-numeric: tabular-nums;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 rgba(0, 0, 0, 0.95),
      0 0 0 1px #000;
  }

  .hardware-pad::before {
    content: "";
    position: absolute;
    z-index: -1;
    width: 30px;
    aspect-ratio: 1;
    border: 1px solid #444;
    border-radius: 50%;
    background: linear-gradient(180deg, #292929, #111);
    box-shadow:
      inset 0 1px 1px rgba(255, 255, 255, 0.1),
      0 2px 3px rgba(0, 0, 0, 0.72);
  }

  .hardware-pad.active,
  .hardware-pad.active:hover:not(:disabled) {
    border-color: #050505;
    background: linear-gradient(180deg, #252525, #111 58%, #070707);
    color: #050505;
    font-weight: 760;
  }

  .hardware-pad.active::before {
    border-color: #d6d6d0;
    background: linear-gradient(180deg, #f4f4ef, #b9bab2 62%, #7d7e76);
  }

  .rotate-row {
    display: flex;
    gap: 6px;
    margin-top: 6px;
  }

  .hardware-pad.compact {
    width: 36px;
    min-width: 36px;
    height: 36px;
    min-height: 36px;
    font-size: 16px;
  }

  .hardware-pad.compact::before {
    width: 22px;
  }
</style>
