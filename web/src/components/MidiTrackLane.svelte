<script lang="ts">
  import type {
    MidiPreviewNote,
    MidiTrackSelectionOption,
  } from "../lib/xy/midiImporter";
  import { opXyFactoryTrackDescription } from "../lib/xy/opXyPresets";
  import OpXyPresetPicker from "./OpXyPresetPicker.svelte";

  export let track: MidiTrackSelectionOption;
  export let index: number;
  export let selected = false;
  export let total16ths: number;
  export let laneWidth: number;
  export let barWidth: number;
  export let trackHeight: number;
  export let laneHeaderWidth: number;
  export let selectionUpdating = false;
  export let onToggle: (track: MidiTrackSelectionOption) => void = () => {};
  export let onPresetChange: (
    track: MidiTrackSelectionOption,
    presetId: string,
  ) => void = () => {};

  $: compact = trackHeight < 42;
  $: assignedTrackNumbers = track.assignedOpXyTracks
    .map((trackIndex) => trackIndex + 1)
    .sort((a, b) => a - b);
  $: destinationLabel = formatDestinationLabel(assignedTrackNumbers);
  $: destinationTitle = assignedTrackNumbers.length
    ? assignedTrackNumbers
        .map((trackNumber) => opXyFactoryTrackDescription(trackNumber))
        .join(" · ")
    : "Disabled — not assigned to an OP-XY track";

  function formatDestinationLabel(trackNumbers: number[]): string {
    if (trackNumbers.length === 0) return "off";
    if (trackNumbers.length === 1) return `T${trackNumbers[0]}`;
    const contiguous = trackNumbers.every(
      (trackNumber, index) =>
        index === 0 || trackNumber === trackNumbers[index - 1] + 1,
    );
    return contiguous
      ? `T${trackNumbers[0]}–${trackNumbers.at(-1)}`
      : `T${trackNumbers.join("/")}`;
  }

  function regionStyle(track: MidiTrackSelectionOption, index: number): string {
    const start = Math.max(0, Math.min(total16ths, track.start16ths));
    const end = Math.max(
      start + 0.5,
      Math.min(total16ths, track.end16ths || total16ths),
    );
    const shade = 24 + (index % 6) * 8;
    const noteFill = shade >= 48 ? "#080808" : "#f4f4f4";
    return [
      `left: ${(start / total16ths) * 100}%`,
      `width: ${Math.max(1.5, ((end - start) / total16ths) * 100)}%`,
      `--region-fill: hsl(0 0% ${shade}%)`,
      `--note-fill: ${noteFill}`,
    ].join("; ");
  }

  function noteStyle(
    track: MidiTrackSelectionOption,
    note: MidiPreviewNote,
  ): string {
    const start = Math.max(0, Math.min(total16ths, track.start16ths));
    const end = Math.max(
      start + 0.5,
      Math.min(total16ths, track.end16ths || total16ths),
    );
    const length = Math.max(0.5, end - start);
    const pitchSpan = Math.max(1, track.pitchMax - track.pitchMin);
    const pitchRatio = (note.note - track.pitchMin) / pitchSpan;
    const top = 78 - Math.max(0, Math.min(1, pitchRatio)) * 62;
    return [
      `left: ${Math.max(0, ((note.start16ths - start) / length) * 100)}%`,
      `width: ${Math.max(0.45, (note.duration16ths / length) * 100)}%`,
      `top: ${top}%`,
    ].join("; ");
  }
</script>

<div
  class="midi-lane"
  class:selected
  class:muted={!selected}
  class:compact
  style={`--track-height: ${trackHeight}px; --lane-header-width: ${laneHeaderWidth}px; --bar-width: ${barWidth}px;`}
>
  <span class="lane-header">
    <span class="track-check">
      <input
        type="checkbox"
        checked={selected}
        disabled={selectionUpdating}
        on:click|preventDefault={() => onToggle(track)}
        aria-label={`Include ${track.name}`}
      />
      <span aria-hidden="true"></span>
    </span>
    <span
      class="lane-title"
      title={`GM ${track.programNumber + 1}: ${track.programName} · MIDI channel ${track.channel}`}
    >
      <strong>{track.name}</strong>
      <OpXyPresetPicker
        selectedId={track.presetId}
        trackName={track.name}
        disabled={selectionUpdating || !selected}
        onChange={(presetId) => onPresetChange(track, presetId)}
      />
    </span>
    <span
      class="lane-destination"
      title={destinationTitle}
      aria-label={destinationTitle}>{destinationLabel}</span
    >
  </span>
  <span class="lane-roll" style={`width: ${laneWidth}px;`}>
    <span
      class="midi-region"
      style={regionStyle(track, index)}
      aria-hidden="true"
    >
      {#each track.previewNotes as note (note.id)}
        <span class="midi-note" style={noteStyle(track, note)}></span>
      {/each}
    </span>
  </span>
</div>

<style>
  .midi-lane {
    box-sizing: border-box;
    display: grid;
    grid-template-columns: var(--lane-header-width) minmax(0, 1fr);
    width: 100%;
    min-width: 0;
    height: var(--track-height);
    min-height: var(--track-height);
    border-bottom: 1px solid #292929;
    opacity: 0.46;
    overflow: hidden;
    transition:
      opacity 140ms ease,
      background 140ms ease;
  }

  .midi-lane.selected {
    opacity: 1;
  }

  .midi-lane:hover {
    background: rgba(255, 255, 255, 0.035);
  }

  .lane-header {
    box-sizing: border-box;
    display: grid;
    grid-template-columns: 28px minmax(0, 1fr) 46px;
    align-items: center;
    gap: 10px;
    height: var(--track-height);
    min-height: var(--track-height);
    padding: 8px 12px;
    border-right: 1px solid #333;
    background: #242424;
  }

  .track-check {
    position: relative;
    display: grid;
    place-items: center;
  }

  .track-check input {
    position: absolute;
    opacity: 0;
  }

  .track-check span {
    display: grid;
    width: 18px;
    height: 18px;
    place-items: center;
    border: 1px solid #686868;
    border-radius: 3px;
    background: #111;
  }

  .track-check span::after {
    content: "";
    width: 8px;
    height: 8px;
    background: transparent;
  }

  .track-check input:checked + span::after {
    background: #f4f4f4;
  }

  .lane-title {
    display: grid;
    grid-template-rows: 17px 20px;
    align-content: center;
    min-width: 0;
    gap: 3px;
    overflow: hidden;
  }

  .lane-title strong {
    overflow: hidden;
    font-size: 13px;
    font-weight: 650;
    line-height: 17px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .lane-destination {
    display: grid;
    min-width: 40px;
    min-height: 24px;
    place-items: center;
    border: 1px solid #454545;
    background: #151515;
    color: #d4d4d4;
    font-size: 10px;
    font-weight: 650;
    font-variant-numeric: tabular-nums;
    text-transform: uppercase;
  }

  .lane-roll {
    box-sizing: border-box;
    position: relative;
    width: 100%;
    max-width: 100%;
    height: var(--track-height);
    min-height: var(--track-height);
    background:
      linear-gradient(90deg, rgba(255, 255, 255, 0.11) 1px, transparent 1px),
      linear-gradient(180deg, rgba(255, 255, 255, 0.035), transparent);
    background-size:
      var(--bar-width) 100%,
      100% 100%;
  }

  .midi-region {
    box-sizing: border-box;
    position: absolute;
    top: max(4px, calc(var(--track-height) * 0.11));
    bottom: max(4px, calc(var(--track-height) * 0.11));
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 5px;
    background: var(--region-fill);
  }

  .midi-note {
    position: absolute;
    height: 3px;
    min-width: 2px;
    border-radius: 2px;
    background: var(--note-fill);
    opacity: 0.8;
  }

  .midi-lane.muted .midi-region {
    filter: grayscale(1);
    opacity: 0.58;
  }

  .midi-lane.compact .lane-header {
    grid-template-columns: 22px minmax(0, 1fr) 40px;
    gap: 7px;
    padding: 3px 9px;
  }

  .midi-lane.compact .track-check span {
    width: 16px;
    height: 16px;
  }

  .midi-lane.compact .lane-title {
    grid-template-rows: 17px;
    gap: 0;
  }

  .midi-lane.compact .lane-title strong {
    font-size: 12px;
  }

  .midi-lane.compact .lane-destination {
    min-width: 36px;
    min-height: 20px;
    font-size: 10px;
  }

  @media (max-width: 760px) {
    .midi-lane {
      grid-template-columns: var(--lane-header-width) minmax(0, 1fr);
    }
  }
</style>
