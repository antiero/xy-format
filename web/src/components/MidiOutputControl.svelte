<script lang="ts">
  import { isXYBuddyNativeEmbed } from "../lib/embedMode";
  import {
    isSafariBrowser,
    webMidiOutputService,
    type MidiOutputChoice,
  } from "../lib/webMidi";

  export let target: "soundfont" | "opxy" = "soundfont";
  export let disabled = false;
  export let onReady: () => void = () => {};
  export let onError: (message: string) => void = () => {};

  let outputs: MidiOutputChoice[] = [];
  let selectedOutputId = "";
  let connecting = false;
  const safariNeedsNativeApp = !isXYBuddyNativeEmbed() && isSafariBrowser();

  async function connectOpXy() {
    connecting = true;
    try {
      outputs = await webMidiOutputService.requestOutputs();
      const preferred = webMidiOutputService.preferredOutput(outputs);
      if (!preferred) throw new Error("No MIDI output was found.");
      selectedOutputId = preferred.id;
      webMidiOutputService.selectOutput(preferred.id);
      target = "opxy";
      onReady();
    } catch (error) {
      onError(
        error instanceof Error ? error.message : "MIDI output unavailable",
      );
    } finally {
      connecting = false;
    }
  }

  function changeOutput(event: Event) {
    selectedOutputId = (event.currentTarget as HTMLSelectElement).value;
    webMidiOutputService.selectOutput(selectedOutputId);
    target = "opxy";
  }
</script>

<button
  type="button"
  class:active={target === "opxy"}
  disabled={disabled || connecting || safariNeedsNativeApp}
  title={safariNeedsNativeApp
    ? "Safari MIDI output is available in the XYBuddy app."
    : "Send notes to OP-XY tracks 1–8. Browse sounds on the device, then choose the matching lane sound here."}
  aria-label="Connect OP-XY MIDI output"
  on:click={connectOpXy}
  >{connecting ? "connect" : target === "opxy" ? "op-xy" : "midi out"}</button
>
{#if outputs.length > 1}
  <select
    class="midi-output-select"
    value={selectedOutputId}
    aria-label="MIDI output device"
    title="Choose a MIDI output device"
    on:change={changeOutput}
  >
    {#each outputs as output (output.id)}
      <option value={output.id}>{output.name}</option>
    {/each}
  </select>
{/if}
{#if target === "opxy"}
  <span
    class="midi-route"
    title="The generated project assigns OP-XY tracks 1–8 to MIDI channels 1–8. Configure the current OP-XY project the same way for pre-export preview."
    >T1–T8 · CH1–8</span
  >
{/if}

<style>
  .midi-output-select,
  .midi-route {
    border: 1px solid #313131;
    background: #0a0a0a;
    color: var(--xy-text-muted);
    padding: 6px 8px;
    font-size: 10px;
    font-variant-numeric: tabular-nums;
    text-transform: uppercase;
  }

  .midi-output-select {
    max-width: 170px;
    height: 30px;
  }
</style>
