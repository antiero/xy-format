<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import {
    fetchStats,
    STATS_UPDATED_EVENT,
    type XYBuddyStats,
  } from "../lib/stats";

  let totalSteps: number | null = null;

  function formattedSteps(value: number): string {
    return new Intl.NumberFormat(undefined, {
      maximumFractionDigits: 0,
    }).format(value);
  }

  function handleStatsUpdated(event: Event): void {
    const stats = (event as CustomEvent<XYBuddyStats>).detail;
    if (Number.isFinite(stats?.totalSteps)) {
      totalSteps = Math.max(0, Math.floor(stats.totalSteps));
    }
  }

  onMount(() => {
    let mounted = true;

    fetchStats().then((stats) => {
      if (mounted) totalSteps = stats?.totalSteps ?? null;
    });

    window.addEventListener(STATS_UPDATED_EVENT, handleStatsUpdated);

    return () => {
      mounted = false;
      window.removeEventListener(STATS_UPDATED_EVENT, handleStatsUpdated);
    };
  });

  onDestroy(() => {
    window.removeEventListener(STATS_UPDATED_EVENT, handleStatsUpdated);
  });
</script>

{#if totalSteps !== null}
  <p class="conversion-counter" aria-label="OP-XY steps converted so far">
    {formattedSteps(totalSteps)} OP-XY steps converted so far.
  </p>
{/if}

<style>
  .conversion-counter {
    margin: 7px 0 0;
    color: var(--xy-text-muted);
    font-size: 12px;
    line-height: 1.35;
    font-variant-numeric: tabular-nums;
  }
</style>
