<script lang="ts">
  import opxySvg from "../assets/opxy.svg";
  import type { DisplayMessage } from "../stores/project";
  import OpXyDisplay from "./OpXyDisplay.svelte";

  type ViewBoxRect = {
    x: number;
    y: number;
    w: number;
    h: number;
  };

  type Hotspot = {
    id: "open-xy" | "import-midi";
    label: string;
    rect: ViewBoxRect;
    message: DisplayMessage;
  };

  export let tempo = 120;
  export let message: DisplayMessage | null = null;
  export let dragging = false;
  export let importState: "idle" | "processing" = "idle";
  export let onOpenXY: () => void = () => {};
  export let onImportMidi: () => void = () => {};

  const VIEWBOX_WIDTH = 740;
  const VIEWBOX_HEIGHT = 265;
  const SCREEN_INNER: ViewBoxRect = { x: 177, y: 19, w: 147.5, h: 64 };
  const OPEN_XY_HOTSPOT: Hotspot = {
    id: "open-xy",
    label: "Open .xy project",
    rect: { x: 171.211, y: 12.16, w: 159.11, h: 79.45 },
    message: { text: "TAP TO OPEN", tone: "neutral" },
  };
  const IMPORT_HOTSPOT: Hotspot = {
    id: "import-midi",
    label: "Import MIDI or .xy file",
    rect: { x: 12.063, y: 12.013, w: 79.574, h: 79.595 },
    message: { text: "CHOOSE FILE", tone: "neutral" },
  };
  const HOTSPOTS: Hotspot[] = [OPEN_XY_HOTSPOT, IMPORT_HOTSPOT];

  let hoverMessage: DisplayMessage | null = null;

  function rectStyle(rect: ViewBoxRect): string {
    return [
      `left: ${(rect.x / VIEWBOX_WIDTH) * 100}%`,
      `top: ${(rect.y / VIEWBOX_HEIGHT) * 100}%`,
      `width: ${(rect.w / VIEWBOX_WIDTH) * 100}%`,
      `height: ${(rect.h / VIEWBOX_HEIGHT) * 100}%`,
    ].join("; ");
  }

  function popoverStyle(rect: ViewBoxRect): string {
    return [
      `--popover-x: ${((rect.x + rect.w / 2) / VIEWBOX_WIDTH) * 100}%`,
      `--popover-y: ${(rect.y / VIEWBOX_HEIGHT) * 100}%`,
    ].join("; ");
  }

  function clearHoverMessage(hotspot: Hotspot): void {
    if (hoverMessage?.text === hotspot.message.text) {
      hoverMessage = null;
    }
  }

  function triggerHotspot(hotspot: Hotspot): void {
    if (hotspot.id === "open-xy") {
      onOpenXY();
    } else {
      onImportMidi();
    }
  }

  $: activeMessage = dragging
    ? ({ text: "DROP XY MIDI", tone: "neutral" } satisfies DisplayMessage)
    : (hoverMessage ?? message);
  $: importPopoverLabel =
    importState === "processing"
      ? "reading"
      : dragging
        ? "drop file"
        : "import";
</script>

<div class="opxy-hardware" class:dragging aria-label="OP-XY project launcher">
  <img
    class="opxy-hardware-art"
    src={opxySvg}
    alt="OP-XY hardware layout"
    draggable="false"
  />

  <div
    class="opxy-screen-overlay"
    style={rectStyle(SCREEN_INNER)}
    aria-hidden="true"
  >
    <OpXyDisplay
      variant="embedded"
      mode="idle"
      fileName=""
      modified={false}
      {tempo}
      counts={{ errors: 0, warnings: 0, info: 0 }}
      isPlaying={false}
      progress={dragging ? 0.56 : 0.28}
      message={activeMessage}
      activeLabel={dragging ? "DROP" : "NO PROJECT"}
    />
  </div>

  <button
    type="button"
    class="launch-import-popover"
    class:processing={importState === "processing"}
    class:drag-ready={dragging}
    style={popoverStyle(OPEN_XY_HOTSPOT.rect)}
    aria-label="Import MIDI or XY file"
    aria-busy={importState === "processing"}
    title="Import MIDI or .xy file"
    disabled={importState === "processing"}
    on:mouseenter={() => (hoverMessage = IMPORT_HOTSPOT.message)}
    on:mouseleave={() => clearHoverMessage(IMPORT_HOTSPOT)}
    on:focus={() => (hoverMessage = IMPORT_HOTSPOT.message)}
    on:blur={() => clearHoverMessage(IMPORT_HOTSPOT)}
    on:click={onImportMidi}
  >
    {#if importState === "processing"}
      <span class="popover-loader" aria-hidden="true">
        <span></span>
        <span></span>
        <span></span>
      </span>
    {/if}
    <span class="popover-text" aria-live="polite">{importPopoverLabel}</span>
  </button>

  {#each HOTSPOTS as hotspot}
    <button
      type="button"
      class={`hardware-hotspot hotspot-${hotspot.id}`}
      style={rectStyle(hotspot.rect)}
      aria-label={hotspot.label}
      on:mouseenter={() => (hoverMessage = hotspot.message)}
      on:mouseleave={() => clearHoverMessage(hotspot)}
      on:focus={() => (hoverMessage = hotspot.message)}
      on:blur={() => clearHoverMessage(hotspot)}
      on:click={() => triggerHotspot(hotspot)}
    >
      <span>{hotspot.label}</span>
    </button>
  {/each}
</div>

<style>
  .opxy-hardware {
    position: relative;
    width: min(94vw, 1180px);
    aspect-ratio: 740 / 265;
    color: var(--xy-text);
    user-select: none;
  }

  .opxy-hardware-art {
    position: absolute;
    inset: 0;
    display: block;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }

  .opxy-screen-overlay,
  .hardware-hotspot {
    position: absolute;
  }

  .opxy-screen-overlay {
    z-index: 2;
    pointer-events: none;
  }

  .launch-import-popover {
    position: absolute;
    z-index: 4;
    top: var(--popover-y);
    left: clamp(64px, var(--popover-x), calc(100% - 64px));
    display: inline-flex;
    min-width: 126px;
    min-height: 54px;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 0 28px;
    border: 0;
    border-radius: 999px;
    background: #1a2d3e;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.16),
      0 14px 30px rgba(0, 0, 0, 0.34);
    color: #f4f4f0;
    font-size: 26px;
    font-weight: 360;
    line-height: 1;
    letter-spacing: 0;
    text-transform: lowercase;
    transform: translate(-50%, calc(-100% - 20px));
    animation: popover-breathe 3.8s ease-in-out infinite;
  }

  .launch-import-popover::before {
    content: "";
    position: absolute;
    inset: -5px;
    border: 1px solid rgba(244, 244, 240, 0.18);
    border-radius: inherit;
    opacity: 0;
    pointer-events: none;
    animation: popover-pulse 3.8s ease-in-out infinite;
  }

  .launch-import-popover::after {
    content: "";
    position: absolute;
    bottom: -16px;
    left: 50%;
    width: 0;
    height: 0;
    border-top: 17px solid #1a2d3e;
    border-right: 15px solid transparent;
    border-left: 15px solid transparent;
    transform: translateX(-50%);
  }

  .launch-import-popover:hover:not(:disabled),
  .launch-import-popover:focus-visible {
    background: #22384d;
    color: #fffdfa;
    outline: 1px solid rgba(247, 247, 242, 0.84);
    outline-offset: 4px;
  }

  .launch-import-popover:active:not(:disabled) {
    transform: translate(-50%, calc(-100% - 18px));
  }

  .launch-import-popover:disabled {
    cursor: wait;
    opacity: 1;
  }

  .launch-import-popover.drag-ready {
    background: #24394c;
  }

  .launch-import-popover.processing {
    min-width: 150px;
    animation: popover-processing 1.2s ease-in-out infinite;
  }

  .popover-text {
    position: relative;
    z-index: 1;
    white-space: nowrap;
  }

  .popover-loader {
    position: relative;
    z-index: 1;
    display: inline-grid;
    grid-template-columns: repeat(3, 6px);
    gap: 5px;
  }

  .popover-loader span {
    width: 6px;
    height: 6px;
    border-radius: 999px;
    background: currentColor;
    animation: loader-dot 820ms ease-in-out infinite;
  }

  .popover-loader span:nth-child(2) {
    animation-delay: 120ms;
  }

  .popover-loader span:nth-child(3) {
    animation-delay: 240ms;
  }

  .hardware-hotspot {
    z-index: 3;
    min-height: 0;
    padding: 0;
    border: 0;
    border-radius: 5px;
    background: transparent;
    box-shadow: none;
    color: transparent;
  }

  .hardware-hotspot:hover,
  .hardware-hotspot:focus-visible {
    outline: 1px solid rgba(247, 247, 242, 0.72);
    outline-offset: 2px;
    background: rgba(247, 247, 242, 0.035);
  }

  .hardware-hotspot:active {
    transform: none;
    background: rgba(247, 247, 242, 0.06);
  }

  .hardware-hotspot span {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  .dragging::after {
    content: "";
    position: absolute;
    inset: -2%;
    z-index: 1;
    border: 1px solid rgba(247, 247, 242, 0.22);
    pointer-events: none;
  }

  @keyframes popover-breathe {
    0%,
    100% {
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.16),
        0 14px 30px rgba(0, 0, 0, 0.34);
    }

    45% {
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.2),
        0 18px 34px rgba(0, 0, 0, 0.4);
    }
  }

  @keyframes popover-pulse {
    0%,
    72%,
    100% {
      opacity: 0;
      transform: scale(0.97);
    }

    24% {
      opacity: 0.56;
      transform: scale(1.04);
    }
  }

  @keyframes popover-processing {
    0%,
    100% {
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.16),
        0 14px 30px rgba(0, 0, 0, 0.34);
    }

    50% {
      box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.24),
        0 0 0 5px rgba(244, 244, 240, 0.055),
        0 18px 36px rgba(0, 0, 0, 0.42);
    }
  }

  @keyframes loader-dot {
    0%,
    100% {
      opacity: 0.28;
      transform: translateY(0);
    }

    50% {
      opacity: 1;
      transform: translateY(-3px);
    }
  }

  @media (max-width: 620px) {
    .launch-import-popover {
      min-width: 96px;
      min-height: 42px;
      padding: 0 20px;
      font-size: 18px;
      transform: translate(-50%, calc(-100% - 14px));
    }

    .launch-import-popover::after {
      bottom: -12px;
      border-top-width: 13px;
      border-right-width: 12px;
      border-left-width: 12px;
    }

    .launch-import-popover.processing {
      min-width: 124px;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .launch-import-popover,
    .launch-import-popover::before,
    .launch-import-popover.processing,
    .popover-loader span {
      animation: none;
    }
  }
</style>
