<script lang="ts">
  type EditorIconName =
    | "undo"
    | "redo"
    | "copy"
    | "cut"
    | "paste"
    | "delete"
    | "audition"
    | "fit"
    | "global"
    | "compress"
    | "expand"
    | "track"
    | "scene"
    | "previous"
    | "next";

  export let icon: EditorIconName;
  export let label: string;
  export let disabled = false;
  export let danger = false;
  export let active = false;
  export let pressed: boolean | undefined = undefined;
  export let onClick: () => void = () => {};
</script>

<button
  type="button"
  class="editor-icon-button"
  class:danger
  class:active
  {disabled}
  aria-label={label}
  aria-pressed={pressed}
  title={label}
  on:click={onClick}
>
  <svg viewBox="0 0 20 20" aria-hidden="true">
    {#if icon === "undo"}
      <path d="M8 5 4 8.5 8 12"></path>
      <path d="M4.5 8.5h6.25a4.25 4.25 0 0 1 4.25 4.25V15"></path>
    {:else if icon === "redo"}
      <path d="m12 5 4 3.5-4 3.5"></path>
      <path d="M15.5 8.5H9.25A4.25 4.25 0 0 0 5 12.75V15"></path>
    {:else if icon === "copy"}
      <rect x="7" y="6" width="8" height="9" rx="1"></rect>
      <path
        d="M12.5 6V4.5A1.5 1.5 0 0 0 11 3H5a1.5 1.5 0 0 0-1.5 1.5v7A1.5 1.5 0 0 0 5 13h2"
      ></path>
    {:else if icon === "cut"}
      <circle cx="5" cy="5" r="2"></circle>
      <circle cx="5" cy="15" r="2"></circle>
      <path d="m6.7 6.1 8.8 7.4M6.7 13.9 15.5 6.5M10 10l-1.2 1"></path>
    {:else if icon === "paste"}
      <path
        d="M7 5H5.5A1.5 1.5 0 0 0 4 6.5v9A1.5 1.5 0 0 0 5.5 17h7a1.5 1.5 0 0 0 1.5-1.5V14"
      ></path>
      <rect x="7" y="3" width="6" height="4" rx="1"></rect>
      <path d="M11 11h5m0 0-2-2m2 2-2 2"></path>
    {:else if icon === "delete"}
      <path d="M4 6h12M8 3h4l1 3H7l1-3Zm-2 3 1 11h6l1-11M9 9v5m2-5v5"></path>
    {:else if icon === "audition"}
      <path
        d="M3.5 8h3l4-3.25v10.5L6.5 12h-3zM13 7a4 4 0 0 1 0 6M14.5 4.75a7 7 0 0 1 0 10.5"
      ></path>
    {:else if icon === "fit"}
      <path d="M3 7V3h4M13 3h4v4M17 13v4h-4M7 17H3v-4"></path>
      <path d="M7 10h6"></path>
    {:else if icon === "global"}
      <circle cx="10" cy="10" r="7"></circle>
      <path d="M3 10h14M10 3a11 11 0 0 1 0 14M10 3a11 11 0 0 0 0 14"></path>
    {:else if icon === "compress"}
      <path d="M4 3v4h4M16 3v4h-4M4 17v-4h4M16 17v-4h-4"></path>
      <path d="m4 7 4-4m8 4-4-4M4 13l4 4m8-4-4 4"></path>
    {:else if icon === "expand"}
      <path d="M8 7H4V3M12 7h4V3M8 13H4v4M12 13h4v4"></path>
      <path d="M8 7 4 3m8 4 4-4m-8 10-4 4m8-4 4 4"></path>
    {:else if icon === "track"}
      <path d="M4 5h12M4 10h8M4 15h10"></path>
      <circle cx="15" cy="10" r="1.5"></circle>
    {:else if icon === "scene"}
      <rect x="3" y="3" width="6" height="6" rx="1"></rect>
      <rect x="11" y="3" width="6" height="6" rx="1"></rect>
      <rect x="3" y="11" width="6" height="6" rx="1"></rect>
      <rect x="11" y="11" width="6" height="6" rx="1"></rect>
    {:else if icon === "previous"}
      <path d="m12.5 4-6 6 6 6"></path>
    {:else}
      <path d="m7.5 4 6 6-6 6"></path>
    {/if}
  </svg>
</button>

<style>
  .editor-icon-button {
    display: grid;
    width: 31px;
    min-width: 31px;
    height: 31px;
    min-height: 31px;
    padding: 0;
    place-items: center;
  }

  svg {
    width: 16px;
    height: 16px;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.5;
  }

  .danger:not(:disabled) {
    color: var(--xy-red-led);
  }

  .active,
  .active:hover:not(:disabled) {
    border-color: var(--xy-white-led);
    background: var(--xy-white-led);
    color: #050505;
  }
</style>
