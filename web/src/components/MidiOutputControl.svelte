<script lang="ts">
  import { isXYBuddyNativeEmbed } from "../lib/embedMode";
  import {
    isSafariBrowser,
    webMidiOutputService,
    XYBUDDY_TESTFLIGHT_URL,
    type MidiOutputChoice,
  } from "../lib/webMidi";

  export let target: "soundfont" | "opxy" = "soundfont";
  export let disabled = false;
  export let onReady: () => void = () => {};
  export let onError: (message: string) => void = () => {};

  let outputs: MidiOutputChoice[] = [];
  let selectedOutputId = "";
  let connecting = false;
  const showSafariHandoff = !isXYBuddyNativeEmbed() && isSafariBrowser();

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
  class:active={target === "soundfont"}
  title="Preview with the General MIDI SoundFont"
  aria-label="Preview with the General MIDI SoundFont"
  on:click={() => (target = "soundfont")}>gm</button
>
<button
  type="button"
  class:active={target === "opxy"}
  disabled={disabled || connecting || showSafariHandoff}
  title="Send notes to OP-XY tracks 1–8. Browse sounds on the device, then choose the matching lane sound here."
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
{#if showSafariHandoff}
  <a
    href={XYBUDDY_TESTFLIGHT_URL}
    target="_blank"
    rel="noreferrer"
    aria-label="Safari cannot output Web MIDI. Download the XYBuddy app for native OP-XY preview."
    title="Safari cannot send Web MIDI. Use XYBuddy for native OP-XY MIDI output."
    >SAFARI MIDI → XYBUDDY APP</a
  >
{/if}

<style>
  a,
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

  a {
    text-decoration: none;
  }

  a:hover,
  a:focus-visible {
    color: var(--xy-text);
    border-color: #666;
  }

  .midi-output-select {
    max-width: 170px;
    height: 30px;
  }
</style>
