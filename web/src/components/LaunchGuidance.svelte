<script lang="ts">
  const steps = [
    {
      number: "1",
      label: "import",
      detail: "drop a MIDI file or open an OP-XY .xy project",
    },
    {
      number: "2",
      label: "shape",
      detail: "choose tracks, preview the result, and name the project",
    },
    {
      number: "3",
      label: "export",
      detail: "download .xy or save to OP-XY from the Mac app",
    },
  ];
</script>

<section class="launch-guidance" aria-label="How XY Buddy works">
  <p>
    import a midi file or op-xy project → tweak it → export .xy for op-xy or
    midi for your daw.
  </p>

  <ol class="launch-steps" aria-label="XY Buddy workflow">
    {#each steps as step}
      <li
        title={step.detail}
        aria-label={`${step.number}. ${step.label}. ${step.detail}`}
      >
        <span class="step-number" aria-hidden="true">{step.number}</span>
        <span>{step.label}</span>
      </li>
    {/each}
  </ol>
</section>

<style>
  .launch-guidance {
    display: grid;
    width: min(680px, 100%);
    justify-items: center;
    gap: 15px;
    color: var(--xy-text-muted);
    text-align: center;
  }

  .launch-guidance p {
    max-width: 650px;
    margin: 0;
    color: var(--xy-text-muted);
    font-size: clamp(12px, 1.35vw, 14px);
    font-weight: 360;
    line-height: 1.55;
    text-wrap: balance;
  }

  .launch-steps {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 10px clamp(16px, 3vw, 28px);
    margin: 0;
    padding: 0;
    color: var(--xy-text-dim);
    font-size: 10px;
    line-height: 1;
    list-style: none;
    text-transform: uppercase;
  }

  .launch-steps li {
    display: inline-flex;
    min-height: 22px;
    align-items: center;
    gap: 7px;
    white-space: nowrap;
  }

  .step-number {
    display: inline-grid;
    width: 18px;
    height: 18px;
    place-items: center;
    border: 1px solid rgba(247, 247, 242, 0.26);
    border-radius: 999px;
    color: var(--xy-text-muted);
    font-size: 9px;
    font-variant-numeric: tabular-nums;
  }

  @media (max-width: 620px) {
    .launch-guidance {
      gap: 13px;
      padding: 0 6px;
    }

    .launch-guidance p {
      font-size: 12px;
      line-height: 1.5;
    }
  }
</style>
