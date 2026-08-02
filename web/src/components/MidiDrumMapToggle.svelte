<script lang="ts">
  import EditorToggle from "./EditorToggle.svelte";

  export let checked = true;
  export let disabled = false;
  export let onChange: (checked: boolean) => void = () => {};

  const tooltip =
    "Enable this option to map GM Drum MIDI to the OP-XY's percussion drum map.";
</script>

<EditorToggle {checked} {disabled} label="Map GM Drums" {tooltip} {onChange} />
