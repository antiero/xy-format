<script lang="ts">
  import { tick } from "svelte";
  import {
    OP_XY_FACTORY_CATEGORIES,
    OP_XY_FACTORY_PRESET_CATALOG,
    opXyPresetById,
    type OpXyFactoryPresetCatalogEntry,
    type OpXyPresetCategory,
  } from "../lib/xy/opXyPresets";

  export let selectedId: string;
  export let trackName: string;
  export let disabled = false;
  export let onChange: (presetId: string) => void = () => {};

  let triggerElement: HTMLButtonElement;
  let dialogElement: HTMLDialogElement;
  let activeCategory: OpXyPresetCategory = "bass";
  let dialogStyle = "";

  $: selectedPreset = opXyPresetById(selectedId);
  $: selectedLabel = selectedPreset?.label ?? "choose sound";
  $: activePresets = OP_XY_FACTORY_PRESET_CATALOG.filter(
    (preset) => preset.category === activeCategory,
  );

  function positionDialog(): void {
    const rect = triggerElement.getBoundingClientRect();
    const width = Math.min(380, window.innerWidth - 16);
    const height = Math.min(420, window.innerHeight - 16);
    const left = Math.max(
      8,
      Math.min(rect.left, window.innerWidth - width - 8),
    );
    const below = rect.bottom + 6;
    const top =
      below + height <= window.innerHeight - 8
        ? below
        : Math.max(8, rect.top - height - 6);
    dialogStyle = [
      `--picker-left: ${left}px`,
      `--picker-top: ${top}px`,
      `--picker-width: ${width}px`,
      `--picker-height: ${height}px`,
    ].join("; ");
  }

  async function openBrowser(): Promise<void> {
    if (disabled) return;
    activeCategory = selectedPreset?.category ?? "bass";
    positionDialog();
    dialogElement.showModal();
    await tick();
    dialogElement
      .querySelector<HTMLElement>("[aria-current='true']")
      ?.scrollIntoView({ block: "nearest" });
  }

  function choosePreset(preset: OpXyFactoryPresetCatalogEntry): void {
    if (!preset.available) return;
    onChange(preset.id);
    dialogElement.close();
  }

  function closeFromBackdrop(event: MouseEvent): void {
    if (event.target === dialogElement) dialogElement.close();
  }
</script>

<span class="picker-root">
  <button
    bind:this={triggerElement}
    type="button"
    class="preset-trigger"
    {disabled}
    aria-label={`OP-XY sound for ${trackName}: ${selectedLabel}`}
    aria-haspopup="dialog"
    title={`Choose the OP-XY sound for ${trackName}`}
    on:click={openBrowser}
  >
    <span>{selectedLabel}</span>
    <i aria-hidden="true"></i>
  </button>

  <dialog
    bind:this={dialogElement}
    class="preset-dialog"
    style={dialogStyle}
    aria-label={`Choose the OP-XY sound for ${trackName}`}
    on:click={closeFromBackdrop}
    on:close={() => triggerElement?.focus()}
  >
    <div class="browser-shell">
      <nav aria-label="OP-XY preset categories">
        {#each OP_XY_FACTORY_CATEGORIES as category}
          <button
            type="button"
            class:active={category === activeCategory}
            aria-pressed={category === activeCategory}
            on:click={() => (activeCategory = category)}
          >
            {category}
          </button>
        {/each}
      </nav>

      <section aria-label={`${activeCategory} factory presets`}>
        <header>
          <strong>{activeCategory}</strong>
          <span>{activePresets.length}</span>
        </header>
        <div class="preset-list">
          {#each activePresets as preset (preset.id)}
            <button
              type="button"
              class:available={preset.available}
              aria-current={preset.id === selectedId ? "true" : undefined}
              aria-disabled={!preset.available}
              aria-label={preset.available
                ? preset.label
                : `${preset.label}, sound capture needed`}
              title={preset.available
                ? `Use ${preset.label}`
                : `${preset.label} needs a device sound-state capture before export`}
              on:click={() => choosePreset(preset)}
            >
              <span>{preset.label}</span>
              {#if preset.id === selectedId}<i aria-hidden="true"></i>{/if}
            </button>
          {/each}
        </div>
      </section>
    </div>
  </dialog>
</span>

<style>
  .picker-root {
    display: block;
    min-width: 0;
    height: 20px;
  }

  .preset-trigger {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 10px;
    align-items: center;
    width: 100%;
    height: 20px;
    min-height: 20px;
    border: 0;
    padding: 0;
    background: transparent;
    color: #9a9a9a;
    font: inherit;
    font-size: 10px;
    line-height: 20px;
    text-align: left;
    text-transform: uppercase;
    cursor: pointer;
  }

  .preset-trigger span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .preset-trigger i {
    width: 6px;
    height: 6px;
    margin: -3px 0 0 1px;
    border-right: 1px solid #858585;
    border-bottom: 1px solid #858585;
    transform: rotate(45deg);
  }

  .preset-trigger:focus-visible {
    outline: 0;
    box-shadow: inset 0 0 0 1px #f4f4f4;
  }

  .preset-trigger:disabled {
    cursor: default;
  }

  .preset-dialog {
    position: fixed;
    inset: auto;
    top: var(--picker-top);
    left: var(--picker-left);
    width: var(--picker-width);
    height: var(--picker-height);
    max-width: calc(100vw - 16px);
    max-height: calc(100vh - 16px);
    box-sizing: border-box;
    margin: 0;
    border: 1px solid #4b4b4b;
    border-radius: 10px;
    padding: 0;
    overflow: hidden;
    background: #1d1d1d;
    color: #ededed;
    box-shadow: 0 18px 60px rgb(0 0 0 / 0.58);
    animation: browser-in 110ms ease-out;
  }

  .preset-dialog::backdrop {
    background: rgb(0 0 0 / 0.18);
  }

  .browser-shell {
    display: grid;
    grid-template-columns: 104px minmax(0, 1fr);
    height: 100%;
  }

  nav {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 10px 8px;
    border-right: 1px solid #343434;
    background: #181818;
  }

  nav button,
  .preset-list button {
    border: 0;
    background: transparent;
    color: inherit;
    font: inherit;
    text-align: left;
  }

  nav button {
    min-height: 34px;
    border-radius: 4px;
    padding: 0 10px;
    color: #777;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    cursor: pointer;
  }

  nav button:hover,
  nav button:focus-visible {
    color: #d8d8d8;
    outline: 0;
  }

  nav button.active {
    background: #2c2c2c;
    color: #f2f2f2;
  }

  section {
    display: grid;
    grid-template-rows: 44px minmax(0, 1fr);
    min-width: 0;
    min-height: 0;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    border-bottom: 1px solid #343434;
  }

  header strong {
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  header span {
    color: #6f6f6f;
    font-size: 10px;
    font-variant-numeric: tabular-nums;
  }

  .preset-list {
    min-height: 0;
    padding: 6px 8px 10px;
    overflow-y: auto;
    overscroll-behavior: contain;
  }

  .preset-list button {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 12px;
    align-items: center;
    width: 100%;
    min-height: 34px;
    border-radius: 4px;
    padding: 0 10px;
    color: #777;
    font-size: 12px;
    letter-spacing: 0.01em;
    cursor: help;
  }

  .preset-list button.available {
    color: #e7e7e7;
    cursor: pointer;
  }

  .preset-list button.available:hover,
  .preset-list button.available:focus-visible,
  .preset-list button[aria-current="true"] {
    background: #303030;
    outline: 0;
  }

  .preset-list button i {
    width: 5px;
    height: 9px;
    border-right: 2px solid #f0f0f0;
    border-bottom: 2px solid #f0f0f0;
    transform: rotate(45deg) translateY(-1px);
  }

  @keyframes browser-in {
    from {
      opacity: 0;
      transform: translateY(-4px) scale(0.99);
    }
  }

  @media (max-width: 480px) {
    .browser-shell {
      grid-template-columns: 86px minmax(0, 1fr);
    }

    nav {
      padding-inline: 6px;
    }

    nav button {
      padding-inline: 8px;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .preset-dialog {
      animation: none;
    }
  }
</style>
