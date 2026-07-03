<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import type {
    MidiTrackSelectionOption,
    MidiTrackSelectionSummary,
  } from "../lib/xy/midiImporter";
  import MidiTrackLane from "./MidiTrackLane.svelte";

  export let selection: MidiTrackSelectionSummary;
  export let selectedIds: ReadonlySet<string>;
  export let playheadActive = false;
  export let selectionUpdating = false;
  export let timelineLength16ths = 0;
  export let playheadPosition16ths = 0;
  export let cycleStart16ths = 0;
  export let cycleEnd16ths = 0;
  export let cycleRangeValid = true;
  export let onToggle: (track: MidiTrackSelectionOption) => void = () => {};
  export let onSeek: (position16ths: number) => void = () => {};
  export let onCycleChange: (
    start16ths: number,
    end16ths: number,
  ) => void = () => {};

  const LANE_HEADER_WIDTH = 284;
  const MOBILE_LANE_HEADER_WIDTH = 238;
  const TRACK_HEIGHT = 46;
  const MIN_CYCLE_16THS = 16;

  let lanesElement: HTMLDivElement;
  let resizeObserver: ResizeObserver | undefined;
  let viewportWidth = 0;
  let cycleDragHandle: "start" | "end" | null = null;
  let draftCycleStart16ths = 0;
  let draftCycleEnd16ths = 0;

  $: total16ths = Math.max(
    MIN_CYCLE_16THS,
    timelineLength16ths || selection.total16ths,
  );
  $: totalBars = Math.max(1, Math.ceil(total16ths / 16));
  $: laneHeaderWidth =
    viewportWidth > 0 && viewportWidth <= 760
      ? MOBILE_LANE_HEADER_WIDTH
      : LANE_HEADER_WIDTH;
  $: laneWidth = Math.max(160, viewportWidth - laneHeaderWidth);
  $: barWidth = Math.max(1, laneWidth / totalBars);
  $: barLabelStep = Math.max(
    1,
    Math.ceil(totalBars / Math.max(1, laneWidth / 58)),
  );
  $: visibleBars = Array.from({ length: totalBars }, (_, bar) => bar).filter(
    (bar) =>
      bar === 0 || bar === totalBars - 1 || (bar + 1) % barLabelStep === 0,
  );
  $: {
    if (!cycleDragHandle) {
      draftCycleStart16ths = cycleStart16ths;
      draftCycleEnd16ths = cycleEnd16ths;
    }
  }
  $: cycleStart = clamp(draftCycleStart16ths, 0, total16ths);
  $: cycleEnd = clamp(
    Math.max(cycleStart + MIN_CYCLE_16THS, draftCycleEnd16ths),
    MIN_CYCLE_16THS,
    total16ths,
  );
  $: cycleLeft = laneHeaderWidth + (cycleStart / total16ths) * laneWidth;
  $: cycleWidth = Math.max(
    2,
    ((cycleEnd - cycleStart) / total16ths) * laneWidth,
  );
  $: playheadLeft =
    laneHeaderWidth +
    (clamp(playheadPosition16ths, 0, total16ths) / total16ths) * laneWidth;
  $: tracksHeight = selection.tracks.length * TRACK_HEIGHT;

  function clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value));
  }

  function measureCanvas() {
    if (!lanesElement) return;
    viewportWidth = lanesElement.clientWidth;
  }

  function positionFromClientX(clientX: number): number | undefined {
    if (!lanesElement || laneWidth <= 0) return;
    const rect = lanesElement.getBoundingClientRect();
    const x = clamp(clientX - rect.left - laneHeaderWidth, 0, laneWidth);
    return (x / laneWidth) * total16ths;
  }

  function seekFromClientX(clientX: number) {
    const position = positionFromClientX(clientX);
    if (position === undefined) return;
    onSeek(
      clamp(position - cycleStart16ths, 0, cycleEnd16ths - cycleStart16ths),
    );
  }

  function handleTimelinePointerDown(event: PointerEvent) {
    if (event.button !== 0) return;
    seekFromClientX(event.clientX);
  }

  function handleTimelineKeydown(event: KeyboardEvent) {
    const step16ths = event.shiftKey ? 16 : 1;
    const current = clamp(
      playheadPosition16ths,
      cycleStart16ths,
      cycleEnd16ths,
    );
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
    onSeek(clamp(next - cycleStart16ths, 0, cycleEnd16ths - cycleStart16ths));
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

  function quantizeCyclePosition(position16ths: number): number {
    return clamp(Math.round(position16ths / 4) * 4, 0, total16ths);
  }

  function updateCycleDraft(clientX: number) {
    const position = positionFromClientX(clientX);
    if (position === undefined || !cycleDragHandle) return;

    const next = quantizeCyclePosition(position);
    if (cycleDragHandle === "start") {
      draftCycleStart16ths = clamp(
        next,
        0,
        draftCycleEnd16ths - MIN_CYCLE_16THS,
      );
    } else {
      draftCycleEnd16ths = clamp(
        next,
        draftCycleStart16ths + MIN_CYCLE_16THS,
        total16ths,
      );
    }
  }

  function handleCyclePointerMove(event: PointerEvent) {
    updateCycleDraft(event.clientX);
  }

  function finishCycleDrag() {
    window.removeEventListener("pointermove", handleCyclePointerMove);
    window.removeEventListener("pointerup", finishCycleDrag);
    cycleDragHandle = null;
    onCycleChange(cycleStart, cycleEnd);
  }

  function beginCycleDrag(handle: "start" | "end", event: PointerEvent) {
    event.preventDefault();
    event.stopPropagation();
    cycleDragHandle = handle;
    updateCycleDraft(event.clientX);
    window.addEventListener("pointermove", handleCyclePointerMove);
    window.addEventListener("pointerup", finishCycleDrag, { once: true });
  }

  onMount(() => {
    measureCanvas();
    resizeObserver = new ResizeObserver(measureCanvas);
    if (lanesElement) resizeObserver.observe(lanesElement);
  });

  onDestroy(() => {
    window.removeEventListener("pointermove", handleCyclePointerMove);
    window.removeEventListener("pointerup", finishCycleDrag);
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
      aria-valuenow={Math.round(clamp(playheadPosition16ths, 0, total16ths))}
      style={`width: ${laneWidth}px;`}
      on:pointerdown={handleTimelinePointerDown}
      on:keydown={handleTimelineKeydown}
    >
      <span
        class="cycle-region"
        class:valid={cycleRangeValid}
        class:invalid={!cycleRangeValid}
        style={`left: ${(cycleStart / total16ths) * 100}%; width: ${((cycleEnd - cycleStart) / total16ths) * 100}%;`}
        aria-hidden="true"
      ></span>
      <button
        type="button"
        class="cycle-handle start"
        class:valid={cycleRangeValid}
        class:invalid={!cycleRangeValid}
        style={`left: ${(cycleStart / total16ths) * 100}%;`}
        tabindex="-1"
        aria-label="Set cycle start"
        on:pointerdown={(event) => beginCycleDrag("start", event)}
      ></button>
      <button
        type="button"
        class="cycle-handle end"
        class:valid={cycleRangeValid}
        class:invalid={!cycleRangeValid}
        style={`left: ${(cycleEnd / total16ths) * 100}%;`}
        tabindex="-1"
        aria-label="Set cycle end"
        on:pointerdown={(event) => beginCycleDrag("end", event)}
      ></button>
      {#each visibleBars as bar}
        <span class="bar-label" style={`left: ${(bar / totalBars) * 100}%;`}
          >{bar + 1}</span
        >
      {/each}
    </div>
  </div>

  <div
    class="cycle-column"
    class:valid={cycleRangeValid}
    class:invalid={!cycleRangeValid}
    style={`left: ${cycleLeft}px; width: ${cycleWidth}px; height: ${tracksHeight}px;`}
    aria-hidden="true"
  ></div>

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
    style={`left: ${playheadLeft}px; height: ${tracksHeight}px;`}
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

  .cycle-region {
    position: absolute;
    top: 0;
    bottom: 0;
    min-width: 2px;
    background: rgba(205, 123, 42, 0.16);
    border-inline: 1px solid rgba(205, 123, 42, 0.78);
    pointer-events: none;
  }

  .cycle-region.valid {
    background: rgba(91, 172, 134, 0.16);
    border-inline-color: rgba(91, 172, 134, 0.78);
  }

  .cycle-handle {
    position: absolute;
    top: 2px;
    z-index: 2;
    width: 12px;
    height: 26px;
    min-height: 0;
    padding: 0;
    border: 1px solid #cd7b2a;
    background: #0d0d0d;
    cursor: ew-resize;
    translate: -6px 0;
  }

  .cycle-handle.valid {
    border-color: #5bac86;
  }

  .cycle-handle.end {
    translate: -6px 0;
  }

  .timeline-bars:focus-visible {
    outline: 1px solid #f2f2f2;
    outline-offset: -2px;
  }

  .timeline-bars .bar-label {
    position: absolute;
    top: 7px;
    translate: 4px 0;
    pointer-events: none;
  }

  .cycle-column {
    position: absolute;
    top: 30px;
    z-index: 1;
    min-width: 2px;
    background: rgba(205, 123, 42, 0.07);
    border-inline: 1px solid rgba(205, 123, 42, 0.22);
    pointer-events: none;
  }

  .cycle-column.valid {
    background: rgba(91, 172, 134, 0.07);
    border-inline-color: rgba(91, 172, 134, 0.22);
  }

  .midi-playhead {
    position: absolute;
    z-index: 4;
    top: 30px;
    width: 2px;
    background: #f2f2f2;
    opacity: 0;
    pointer-events: none;
  }

  .midi-playhead.active {
    opacity: 0.92;
  }
</style>
