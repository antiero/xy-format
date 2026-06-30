<script lang="ts">
  import type {
    DisplayMessage,
    DisplayTone,
    WorkspaceMode,
  } from "../stores/project";

  type ValidationCounts = {
    errors: number;
    warnings: number;
    info: number;
  };

  type DotMatrix = {
    rows: boolean[][];
    columns: number;
    text: string;
  };

  export let mode: WorkspaceMode | "idle" = "idle";
  export let fileName = "";
  export let modified = false;
  export let tempo = 120;
  export let counts: ValidationCounts = { errors: 0, warnings: 0, info: 0 };
  export let isPlaying = false;
  export let progress = 0;
  export let message: DisplayMessage | null = null;
  export let activeLabel = "";
  export let variant: "standalone" | "embedded" = "standalone";

  const modeLabels: Record<WorkspaceMode | "idle", string> = {
    idle: "READY",
    project: "PROJECT",
    daw: "DAW",
    pattern: "PATTERN",
    arrange: "ARRANGE",
    inspect: "INSPECT",
  };

  const glyphs: Record<string, string[]> = {
    " ": ["000", "000", "000", "000", "000", "000", "000"],
    A: ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    B: ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    C: ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    D: ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    E: ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    F: ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    G: ["01111", "10000", "10000", "10011", "10001", "10001", "01110"],
    H: ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    I: ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    J: ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
    K: ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    L: ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    M: ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    N: ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    O: ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    P: ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    Q: ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    R: ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    S: ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    T: ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    U: ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    V: ["10001", "10001", "10001", "10001", "01010", "01010", "00100"],
    W: ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    X: ["10001", "01010", "00100", "00100", "00100", "01010", "10001"],
    Y: ["10001", "01010", "00100", "00100", "00100", "00100", "00100"],
    Z: ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "10000", "11110", "00001", "00001", "11110"],
    "6": ["01110", "10000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00001", "01110"],
    ".": ["000", "000", "000", "000", "000", "110", "110"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    ":": ["000", "110", "110", "000", "110", "110", "000"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    ">": ["10000", "01000", "00100", "00010", "00100", "01000", "10000"],
    "?": ["01110", "10001", "00001", "00010", "00100", "00000", "00100"],
  };

  const stepCells = Array.from({ length: 16 }, (_, index) => index);

  function clamp(value: number): number {
    if (!Number.isFinite(value)) return 0;
    return Math.max(0, Math.min(1, value));
  }

  function normalizeText(value: string, maxChars: number): string {
    const normalized = value
      .toUpperCase()
      .replace(/\.XY$/, "")
      .replace(/[^A-Z0-9 ./:\-+>]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    const fallback = normalized || "READY";

    if (fallback.length <= maxChars) return fallback;
    if (maxChars <= 1) return ">";
    return `${fallback.slice(0, maxChars - 1)}>`;
  }

  function makeDotMatrix(value: string, maxChars: number): DotMatrix {
    const text = normalizeText(value, maxChars);
    const rows = Array.from({ length: 7 }, () => [] as boolean[]);

    for (const [index, char] of [...text].entries()) {
      const glyph = glyphs[char] ?? glyphs["?"];
      for (let rowIndex = 0; rowIndex < 7; rowIndex += 1) {
        for (const bit of glyph[rowIndex]) {
          rows[rowIndex].push(bit === "1");
        }
        if (index < text.length - 1) rows[rowIndex].push(false);
      }
    }

    return {
      rows,
      columns: Math.max(rows[0]?.length ?? 0, 1),
      text,
    };
  }

  $: normalizedProgress = clamp(progress);
  $: activeStep = Math.floor(normalizedProgress * stepCells.length) % 16;
  $: tone = (message?.tone ??
    (counts.errors > 0
      ? "error"
      : counts.warnings > 0
        ? "warn"
        : isPlaying
          ? "play"
          : "neutral")) as DisplayTone;
  $: displayText =
    message?.text ??
    (fileName ? fileName.replace(/\.[^.]+$/, "") : "midi / xy in");
  $: statusText = fileName
    ? `${modified ? "EDIT" : "SYNC"} ${counts.errors}E ${counts.warnings}W`
    : "xy / midi out";
  $: modeText = modeLabels[mode] ?? "READY";
  $: tempoText = `${Math.round(tempo)}BPM`;
  $: headerModeMatrix = makeDotMatrix(modeText, 7);
  $: headerActiveMatrix = makeDotMatrix(activeLabel || "OP XY", 9);
  $: headerTempoMatrix = makeDotMatrix(tempoText, 7);
  $: mainMatrix = makeDotMatrix(displayText, 12);
  $: statusMatrix = makeDotMatrix(statusText, 18);
</script>

<div
  class={`opxy-display variant-${variant} tone-${tone}`}
  class:playing={isPlaying}
  role="status"
  aria-live="polite"
  aria-label={`Display: ${displayText}. ${statusText}.`}
>
  <div class="display-screen">
    <div class="display-header" aria-hidden="true">
      <div
        class="matrix-shell matrix-small"
        style={`--dot-columns: ${headerModeMatrix.columns};`}
      >
        <div class="dot-matrix">
          {#each headerModeMatrix.rows as row}
            {#each row as isOn}
              <span class:on={isOn}></span>
            {/each}
          {/each}
        </div>
      </div>

      <div
        class="matrix-shell matrix-small matrix-center"
        style={`--dot-columns: ${headerActiveMatrix.columns};`}
      >
        <div class="dot-matrix">
          {#each headerActiveMatrix.rows as row}
            {#each row as isOn}
              <span class:on={isOn}></span>
            {/each}
          {/each}
        </div>
      </div>

      <div
        class="matrix-shell matrix-small matrix-right"
        style={`--dot-columns: ${headerTempoMatrix.columns};`}
      >
        <div class="dot-matrix">
          {#each headerTempoMatrix.rows as row}
            {#each row as isOn}
              <span class:on={isOn}></span>
            {/each}
          {/each}
        </div>
      </div>
    </div>

    <div
      class="matrix-shell matrix-main"
      aria-hidden="true"
      style={`--dot-columns: ${mainMatrix.columns};`}
    >
      <div class="dot-matrix">
        {#each mainMatrix.rows as row}
          {#each row as isOn}
            <span class:on={isOn}></span>
          {/each}
        {/each}
      </div>
    </div>

    <div
      class="matrix-shell matrix-status"
      aria-hidden="true"
      style={`--dot-columns: ${statusMatrix.columns};`}
    >
      <div class="dot-matrix">
        {#each statusMatrix.rows as row}
          {#each row as isOn}
            <span class:on={isOn}></span>
          {/each}
        {/each}
      </div>
    </div>

    <div class="display-steps" aria-hidden="true">
      {#each stepCells as step}
        <span
          class:active={isPlaying && step === activeStep}
          class:passed={isPlaying && step < activeStep}
        ></span>
      {/each}
    </div>
  </div>
</div>

<style>
  .opxy-display {
    aspect-ratio: 480 / 190;
    width: min(100%, 520px);
    min-width: 260px;
    border-radius: 5px;
    padding: 7px;
    background: #050505;
    border: 1px solid #282828;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.08),
      inset 0 -1px 0 #000,
      0 18px 38px rgba(0, 0, 0, 0.42);
    --matrix-on: #f4f2e8;
    --matrix-off: rgba(244, 242, 232, 0.07);
    --matrix-glow: rgba(244, 242, 232, 0.28);
    --step-active: var(--xy-red-led);
  }

  .variant-embedded {
    width: 100%;
    height: 100%;
    min-width: 0;
    aspect-ratio: auto;
    padding: 0;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
  }

  .display-screen {
    height: 100%;
    overflow: hidden;
    border-radius: 2px;
    background: #080909;
    border: 1px solid #151515;
    display: grid;
    grid-template-rows: auto 1fr auto auto;
    align-items: center;
    gap: clamp(7px, 1.5vw, 12px);
    padding: clamp(9px, 2.1vw, 14px);
    box-shadow:
      inset 0 0 0 1px #000,
      inset 0 0 18px rgba(0, 0, 0, 0.72);
  }

  .variant-embedded .display-screen {
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
    grid-template-rows: 1fr auto auto;
    gap: 7%;
    padding: 6% 7% 7%;
  }

  .display-header {
    display: grid;
    grid-template-columns: 0.75fr 1.1fr 0.75fr;
    gap: clamp(8px, 1.6vw, 14px);
    align-items: start;
    min-width: 0;
  }

  .variant-embedded .display-header {
    display: none;
  }

  .matrix-shell {
    --dot-rows: 7;
    --dot-gap: clamp(1px, 0.22vw, 2px);
    width: 100%;
    min-width: 0;
    aspect-ratio: var(--dot-columns) / var(--dot-rows);
  }

  .matrix-small {
    --dot-gap: 1px;
    max-height: 18px;
  }

  .matrix-main {
    justify-self: center;
    width: min(100%, 430px);
    max-height: 68px;
  }

  .variant-embedded .matrix-main {
    width: 96%;
    max-height: none;
    align-self: end;
    --dot-gap: 1px;
  }

  .matrix-status {
    justify-self: center;
    width: min(100%, 410px);
    max-height: 21px;
    --matrix-off: rgba(244, 242, 232, 0.045);
  }

  .variant-embedded .matrix-status {
    width: 72%;
    max-height: none;
    justify-self: start;
    opacity: 0.76;
    --dot-gap: 1px;
    --matrix-off: rgba(244, 242, 232, 0.035);
  }

  .matrix-center {
    justify-self: center;
  }

  .matrix-right {
    justify-self: end;
  }

  .dot-matrix {
    width: 100%;
    height: 100%;
    display: grid;
    grid-template-columns: repeat(var(--dot-columns), minmax(0, 1fr));
    grid-template-rows: repeat(var(--dot-rows), minmax(0, 1fr));
    gap: var(--dot-gap);
  }

  .dot-matrix span {
    width: 100%;
    height: 100%;
    align-self: center;
    justify-self: center;
    border-radius: 50%;
    background: var(--matrix-off);
    transform: scale(0.7);
  }

  .dot-matrix span.on {
    background: var(--matrix-on);
    box-shadow: 0 0 7px var(--matrix-glow);
  }

  .variant-embedded .dot-matrix span {
    transform: scale(0.92);
  }

  .variant-embedded .matrix-status .dot-matrix span {
    transform: scale(0.72);
  }

  .display-steps {
    display: grid;
    grid-template-columns: repeat(16, 1fr);
    gap: clamp(3px, 0.9vw, 5px);
  }

  .variant-embedded .display-steps {
    gap: 2.4%;
  }

  .display-steps span {
    height: clamp(5px, 1.1vw, 8px);
    border-radius: 50%;
    background: rgba(244, 242, 232, 0.09);
  }

  .variant-embedded .display-steps span {
    height: max(2px, 0.62vw);
  }

  .display-steps span.passed {
    background: rgba(244, 242, 232, 0.38);
  }

  .display-steps span.active {
    background: var(--step-active);
    box-shadow: 0 0 10px rgba(255, 43, 31, 0.6);
  }

  .tone-warn {
    --step-active: var(--xy-yellow-warn);
  }

  .tone-error {
    --step-active: var(--xy-red-led);
  }

  .tone-ok {
    --matrix-glow: rgba(244, 242, 232, 0.34);
  }

  .playing .dot-matrix span.on {
    animation: led-breathe 920ms steps(2, end) infinite alternate;
  }

  @keyframes led-breathe {
    from {
      opacity: 0.78;
    }
    to {
      opacity: 1;
    }
  }

  @media (max-width: 760px) {
    .opxy-display {
      width: 100%;
      min-width: 0;
    }

    .display-header {
      grid-template-columns: 1fr 1fr;
    }

    .matrix-center {
      display: none;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .playing .dot-matrix span.on {
      animation: none !important;
    }
  }
</style>
