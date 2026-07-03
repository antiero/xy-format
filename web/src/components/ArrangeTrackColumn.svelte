<script lang="ts">
  import type { ArrangerTrackColumn } from "../lib/xy/arranger";
  import ArrangePatternCell from "./ArrangePatternCell.svelte";

  export let column: ArrangerTrackColumn;

  $: shade = 18 + column.trackIndex * 7;
  $: activeShade = column.trackIndex < 5 ? 50 + column.trackIndex * 8 : 88;
  $: activeText = activeShade > 72 ? "#050505" : "#f7f5f5";
  $: noteFill = activeShade > 72 ? "#050505" : "#f7f5f5";
</script>

<div
  class="arrange-column"
  class:muted={column.muted}
  style={`--slot-fill: hsl(240 4% ${shade}%); --active-fill: hsl(240 4% ${activeShade}%); --pattern-text: ${activeText}; --note-fill: ${noteFill};`}
>
  <div class="track-header" aria-label={`Track ${column.label}`}>
    <span>{column.label}</span>
  </div>
  <div class="pattern-stack">
    {#each column.slots as slot (slot.row)}
      <ArrangePatternCell {slot} trackLabel={column.label} />
    {/each}
  </div>
</div>

<style>
  .arrange-column {
    position: relative;
    display: grid;
    grid-template-rows: 54px minmax(0, 1fr);
    min-width: 92px;
    border-right: 1px solid rgba(255, 255, 255, 0.13);
  }

  .arrange-column:first-child {
    border-left: 1px solid rgba(255, 255, 255, 0.13);
  }

  .arrange-column.muted {
    filter: saturate(0.2);
  }

  .track-header {
    display: grid;
    place-items: center;
    color: #f7f5f5;
    font-size: 44px;
    font-weight: 360;
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }

  .pattern-stack {
    display: grid;
    grid-template-rows:
      minmax(28px, 1fr)
      minmax(28px, 1fr)
      minmax(28px, 1fr)
      minmax(28px, 1fr)
      54px
      minmax(28px, 1fr)
      minmax(28px, 1fr)
      minmax(28px, 1fr)
      minmax(28px, 1fr);
    align-items: stretch;
  }

  @media (max-width: 760px) {
    .arrange-column {
      min-width: 0;
      grid-template-rows: 46px minmax(0, 1fr);
    }

    .track-header {
      font-size: clamp(24px, 8vw, 34px);
    }
  }
</style>
