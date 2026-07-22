<script lang="ts">
  export let checked = true;
  export let disabled = false;
  export let onChange: (checked: boolean) => void = () => {};

  const tooltip =
    "Enable this option to map GM Drum MIDI to the OP-XY's percussion drum map.";

  function change(event: Event) {
    onChange((event.currentTarget as HTMLInputElement).checked);
  }
</script>

<label class="drum-map-toggle" title={tooltip}>
  <input
    type="checkbox"
    {checked}
    {disabled}
    aria-label={tooltip}
    on:change={change}
  />
  <span aria-hidden="true"></span>
  <strong>Map GM Drums</strong>
</label>

<style>
  .drum-map-toggle {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    min-height: 30px;
    padding: 4px 8px;
    border: 1px solid #313131;
    background: #0a0a0a;
    color: var(--xy-text-muted);
    text-transform: uppercase;
    cursor: pointer;
  }

  input {
    position: absolute;
    opacity: 0;
    pointer-events: none;
  }

  span {
    position: relative;
    display: inline-block;
    width: 28px;
    height: 14px;
    border: 1px solid #555;
    border-radius: 999px;
    background: #121212;
  }

  span::after {
    content: "";
    position: absolute;
    top: 2px;
    left: 2px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #777;
    transition:
      left 120ms ease,
      background 120ms ease;
  }

  input:checked + span {
    border-color: #f3f1ef;
  }

  input:checked + span::after {
    left: 16px;
    background: #f3f1ef;
  }

  input:focus-visible + span {
    outline: 1px solid var(--xy-white-led);
    outline-offset: 2px;
  }

  strong {
    color: inherit;
    font-size: 10px;
    font-weight: 560;
  }
</style>
