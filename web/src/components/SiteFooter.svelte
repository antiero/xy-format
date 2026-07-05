<script lang="ts">
  import ConversionCounter from "./ConversionCounter.svelte";
</script>

<footer class="disclaimer site-footer" aria-label="XYBuddy acknowledgements">
  <p>
    app by <a
      href="https://github.com/antiero/xy-format"
      target="_blank"
      rel="noreferrer">antiero (5of12)</a
    >. independent and not affiliated with teenage engineering.
    <br />made possible by reverse engineering efforts of
    <a
      href="https://github.com/kmorrill/xy-format"
      target="_blank"
      rel="noreferrer">kmorrill</a
    >.
  </p>
  <ConversionCounter />
  <span class="firmware-footnote">supports op-xy firmware 1.1.15 or later.</span
  >
</footer>

<style>
  .site-footer p {
    margin: 0;
  }
</style>
