<script lang="ts">
  import {
    MAX_PROJECT_TEMPO_BPM,
    MIN_PROJECT_TEMPO_BPM,
    normalizeProjectTempoBpm,
  } from "../lib/xy/tempo";
  import {
    announceDisplayMessage,
    dispatchProjectEdit,
  } from "../stores/project";

  export let tempoBpm: number;
  export let onTempoChange: (tempoBpm: number) => void = () => {};

  function commitTempo(event: Event): void {
    const input = event.currentTarget as HTMLInputElement;
    const nextTempo = normalizeProjectTempoBpm(
      Number.parseFloat(input.value),
      tempoBpm,
    );
    input.value = nextTempo.toFixed(1);
    if (nextTempo === tempoBpm) return;

    dispatchProjectEdit({ type: "set-tempo", bpm: nextTempo });
    onTempoChange(nextTempo);
    announceDisplayMessage(`TEMPO ${nextTempo.toFixed(1)} BPM`, "ok");
  }

  function commitOnEnter(event: KeyboardEvent): void {
    if (event.key === "Enter") {
      (event.currentTarget as HTMLInputElement).blur();
    }
  }
</script>

<label
  class="tempo-control"
  title={`Project tempo, ${MIN_PROJECT_TEMPO_BPM} to ${MAX_PROJECT_TEMPO_BPM} BPM`}
>
  <input
    type="number"
    min={MIN_PROJECT_TEMPO_BPM}
    max={MAX_PROJECT_TEMPO_BPM}
    step="0.1"
    inputmode="decimal"
    value={tempoBpm.toFixed(1)}
    aria-label={`Project tempo in BPM, ${MIN_PROJECT_TEMPO_BPM} to ${MAX_PROJECT_TEMPO_BPM}`}
    on:change={commitTempo}
    on:keydown={commitOnEnter}
  />
  <span>BPM</span>
</label>

<style>
  .tempo-control {
    display: inline-flex;
    min-height: 28px;
    align-items: center;
    border: 1px solid #313131;
    background: #0a0a0a;
    color: var(--xy-text-muted);
    font-size: 10px;
    font-variant-numeric: tabular-nums;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .tempo-control:focus-within {
    border-color: var(--xy-white-led);
  }

  .tempo-control input {
    width: 54px;
    min-height: 26px;
    border: 0;
    border-radius: 0;
    background: transparent;
    color: var(--xy-text);
    padding: 0 3px 0 7px;
    text-align: right;
    font-size: 10px;
    font-variant-numeric: tabular-nums;
    appearance: textfield;
  }

  .tempo-control input:focus {
    outline: 0;
  }

  .tempo-control input::-webkit-inner-spin-button,
  .tempo-control input::-webkit-outer-spin-button {
    margin: 0;
    appearance: none;
  }

  .tempo-control span {
    padding-right: 7px;
  }
</style>
