<script lang="ts">
  import type { ArrangerPatternSlot } from "../lib/xy/arranger";

  export let slot: ArrangerPatternSlot;
  export let trackLabel: string;

  $: ariaLabel = slot.exists
    ? `Track ${trackLabel}, pattern ${slot.label}, ${slot.noteCount} notes${slot.active ? ", active" : ""}${slot.muted ? ", muted" : ""}`
    : `Track ${trackLabel}, no pattern`;
</script>

<div
  class="pattern-cell"
  class:active={slot.active}
  class:muted={slot.muted}
  class:missing={!slot.exists}
  aria-label={ariaLabel}
  title={ariaLabel}
>
  {#if slot.exists}
    <span class="pattern-id">{slot.label}</span>
    <span class="note-plane" aria-hidden="true">
      {#each slot.notes as note (note.id)}
        <span
          class="note-dot"
          style={`left: ${note.leftPct}%; top: ${note.topPct}%;`}
        ></span>
      {/each}
    </span>
  {/if}
</div>

<style>
  .pattern-cell {
    position: relative;
    min-height: 42px;
    border-left: 1px solid rgba(255, 255, 255, 0.08);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    background: transparent;
    overflow: hidden;
    opacity: 0.76;
  }

  .pattern-cell.active {
    min-height: 54px;
    border-top: 1px solid rgba(255, 255, 255, 0.7);
    border-bottom: 1px solid rgba(255, 255, 255, 0.7);
    background: var(--active-fill);
    opacity: 1;
  }

  .pattern-cell:not(.active):not(.missing) {
    background: var(--slot-fill);
  }

  .pattern-cell.missing {
    opacity: 0.24;
  }

  .pattern-cell.muted {
    opacity: 0.36;
  }

  .pattern-id {
    position: absolute;
    z-index: 2;
    left: 8px;
    top: 7px;
    color: var(--pattern-text);
    font-size: 13px;
    font-variant-numeric: tabular-nums;
    line-height: 1;
  }

  .note-plane {
    position: absolute;
    inset: 9px 9px 8px 22px;
  }

  .note-dot {
    position: absolute;
    width: 3px;
    height: 3px;
    border-radius: 1px;
    background: var(--note-fill);
    transform: translate(-50%, -50%);
  }

  .pattern-cell.active .note-dot {
    width: 4px;
    height: 4px;
  }
</style>
