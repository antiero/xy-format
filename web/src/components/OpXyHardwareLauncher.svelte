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
  export let onOpenXY: () => void = () => {};
  export let onImportMidi: () => void = () => {};

  const VIEWBOX_WIDTH = 740;
  const VIEWBOX_HEIGHT = 265;
  const SCREEN_INNER: ViewBoxRect = { x: 177, y: 19, w: 147.5, h: 64 };
  const HOTSPOTS: Hotspot[] = [
    {
      id: "open-xy",
      label: "Open .xy project",
      rect: { x: 171.211, y: 12.16, w: 159.11, h: 79.45 },
      message: { text: "OPEN XY", tone: "neutral" },
    },
    {
      id: "import-midi",
      label: "Import MIDI",
      rect: { x: 12.063, y: 12.013, w: 79.574, h: 79.595 },
      message: { text: "IMPORT MIDI", tone: "neutral" },
    },
  ];

  let hoverMessage: DisplayMessage | null = null;

  function rectStyle(rect: ViewBoxRect): string {
    return [
      `left: ${(rect.x / VIEWBOX_WIDTH) * 100}%`,
      `top: ${(rect.y / VIEWBOX_HEIGHT) * 100}%`,
      `width: ${(rect.w / VIEWBOX_WIDTH) * 100}%`,
      `height: ${(rect.h / VIEWBOX_HEIGHT) * 100}%`,
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
</style>
