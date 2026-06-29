<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import type {
    MidiTrackSelectionOption,
    MidiTrackSelectionSummary,
  } from "../lib/xy/midiImporter";
  import MidiTrackLane from "./MidiTrackLane.svelte";

  export let selection: MidiTrackSelectionSummary;
  export let selectedIds: ReadonlySet<string>;
  export let progress = 0;
  export let playheadActive = false;
  export let selectionUpdating = false;
  export let timelineLength16ths = 0;
  export let onToggle: (track: MidiTrackSelectionOption) => void = () => {};
  export let onSeek: (position16ths: number) => void = () => {};

  const LANE_HEADER_WIDTH = 284;
  const MOBILE_LANE_HEADER_WIDTH = 238;
  const TRACK_HEIGHT = 46;

  let lanesElement: HTMLDivElement;
  let resizeObserver: ResizeObserver | undefined;
  let viewportWidth = 0;

  $: total16ths = Math.max(16, timelineLength16ths || selection.total16ths);
  $: laneHeaderWidth =
    viewportWidth > 0 && viewportWidth <= 760
      ? MOBILE_LANE_HEADER_WIDTH
      : LANE_HEADER_WIDTH;
  $: laneWidth = Math.max(160, viewportWidth - laneHeaderWidth);
  $: barWidth = Math.max(1, laneWidth / Math.max(1, selection.totalBars));
  $: barLabelStep = Math.max(
    1,
    Math.ceil(selection.totalBars / Math.max(1, laneWidth / 58)),
  );
  $: visibleBars = Array.from(
    { length: selection.totalBars },
    (_, bar) => bar,
  ).filter(
    (bar) =>
      bar === 0 ||
      bar === selection.totalBars - 1 ||
      (bar + 1) % barLabelStep === 0,
  );
  $: playheadLeft =
    laneHeaderWidth + Math.max(0, Math.min(1, progress)) * laneWidth;

  function clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value));
  }

  function measureCanvas() {
    if (!lanesElement) return;
    viewportWidth = lanesElement.clientWidth;
  }

  function seekFromClientX(clientX: number) {
    if (!lanesElement || laneWidth <= 0) return;
    const rect = lanesElement.getBoundingClientRect();
    const x = clamp(clientX - rect.left - laneHeaderWidth, 0, laneWidth);
    onSeek((x / laneWidth) * total16ths);
  }

  function handleTimelinePointerDown(event: PointerEvent) {
    if (event.button !== 0) return;
    seekFromClientX(event.clientX);
  }

  function handleTimelineKeydown(event: KeyboardEvent) {
    const step16ths = event.shiftKey ? 16 : 1;
    const current = clamp(progress, 0, 1) * total16ths;
    let next = current;

    if (event.key === "Home") {
      next = 0;
    } else if (event.key === "End") {
      next = total16ths;
    } else if (event.key === "ArrowLeft") {
      next = current - step16ths;
    } else if (event.key === "ArrowRight") {
      next = current + step16ths;
    } else {
      return;
    }

    event.preventDefault();
    onSeek(clamp(next, 0, total16ths));
  }

  function handleWheel(event: WheelEvent) {
    if (Math.abs(event.deltaX) > Math.abs(event.deltaY)) {
      event.preventDefault();
    }
  }

  function handleCanvasScroll() {
    if (lanesElement && lanesElement.scrollLeft !== 0) {
      lanesElement.scrollLeft = 0;
    }
  }

  onMount(() => {
    measureCanvas();
    resizeObserver = new ResizeObserver(measureCanvas);
    if (lanesElement) resizeObserver.observe(lanesElement);
  });

  onDestroy(() => {
    resizeObserver?.disconnect();
  });
</script>

<div
  class="midi-lanes"
  bind:this={lanesElement}
  on:scroll={handleCanvasScroll}
  on:wheel={handleWheel}
  style={`--lane-header-width: ${laneHeaderWidth}px; --bar-width: ${barWidth}px;`}
>
  <div class="timeline-row">
    <div class="timeline-corner">tracks</div>
    <div
      class="timeline-bars"
      role="slider"
      tabindex="0"
      aria-label="Playback position"
      aria-valuemin="0"
      aria-valuemax={Math.round(total16ths)}
      aria-valuenow={Math.round(clamp(progress, 0, 1) * total16ths)}
      style={`width: ${laneWidth}px;`}
      on:pointerdown={handleTimelinePointerDown}
      on:keydown={handleTimelineKeydown}
    >
      {#each visibleBars as bar}
        <span style={`left: ${(bar / selection.totalBars) * 100}%;`}
          >{bar + 1}</span
        >
      {/each}
    </div>
  </div>

  {#each selection.tracks as track, index (track.id)}
    <MidiTrackLane
      {track}
      {index}
      selected={selectedIds.has(track.id)}
      {total16ths}
      {laneWidth}
      {barWidth}
      trackHeight={TRACK_HEIGHT}
      {laneHeaderWidth}
      {selectionUpdating}
      {onToggle}
    />
  {/each}

  <div
    class="midi-playhead"
    class:active={playheadActive}
    style={`left: ${playheadLeft}px;`}
  ></div>
</div>

<style>
  .midi-lanes {
    box-sizing: border-box;
    position: relative;
    overflow-x: hidden;
    overflow-y: auto;
    min-width: 0;
    height: min(62vh, 720px);
    min-height: 320px;
    max-width: 100%;
    overscroll-behavior: contain;
    scrollbar-width: none;
    touch-action: pan-y;
    background:
      linear-gradient(90deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px),
      #181818;
    background-size: var(--bar-width) 100%;
  }

  .midi-lanes::-webkit-scrollbar {
    width: 0;
    height: 0;
  }

  .timeline-row {
    box-sizing: border-box;
    display: grid;
    grid-template-columns: var(--lane-header-width) minmax(0, 1fr);
    width: 100%;
    position: sticky;
    top: 0;
    z-index: 3;
    height: 30px;
    min-height: 30px;
    background: #0d0d0d;
    color: #8f8f8f;
    font-size: 10px;
    text-transform: uppercase;
  }

  .timeline-corner,
  .timeline-bars {
    box-sizing: border-box;
    border-bottom: 1px solid #333;
  }

  .timeline-corner {
    display: flex;
    align-items: center;
    padding-left: 13px;
    border-right: 1px solid #333;
    background: #111;
  }

  .timeline-bars {
    position: relative;
    height: 30px;
    min-width: 0;
    cursor: pointer;
    background: linear-gradient(
      90deg,
      rgba(255, 255, 255, 0.1) 1px,
      transparent 1px
    );
    background-size: var(--bar-width) 100%;
  }

  .timeline-bars:focus-visible {
    outline: 1px solid #f2f2f2;
    outline-offset: -2px;
  }

  .timeline-bars span {
    position: absolute;
    top: 7px;
    translate: 4px 0;
    pointer-events: none;
  }

  .midi-playhead {
    position: absolute;
    z-index: 4;
    top: 30px;
    bottom: 0;
    width: 2px;
    background: #f2f2f2;
    opacity: 0;
    pointer-events: none;
  }

  .midi-playhead.active {
    opacity: 0.92;
  }
</style>
