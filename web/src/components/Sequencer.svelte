<script lang="ts">
  import { projectStore, activeTrackStore, activePatternStore } from '../stores/project';
  import { STEP_TICKS } from '../lib/xy/image_writer';
  import { Midi } from '@tonejs/midi';

  // Track colors mimicking TE aesthetic
  const trackColors = [
    '#ff3b30', '#ff9500', '#ffcc00', '#4cd964',
    '#5ac8fa', '#007aff', '#5856d6', '#ff2d55',
    '#ff3b30', '#ff9500', '#ffcc00', '#4cd964',
    '#5ac8fa', '#007aff', '#5856d6', '#ff2d55'
  ];

  let notes: {tick: number, gate: number, note: number, velocity: number}[] = [];

  $: if ($projectStore && $activeTrackStore && $activePatternStore !== undefined) {
    try {
        const patternCount = $projectStore.getPatternCount($activeTrackStore);
        if ($activePatternStore >= patternCount) {
           activePatternStore.set(0);
        } else {
           notes = $projectStore.getNotes($activeTrackStore, $activePatternStore);
        }
    } catch(e) {
        notes = [];
    }
  }

  // Define grid
  const steps = 64; // Max steps
  const noteRange = [24, 108]; // C1 to C8 roughly
  const totalNotes = noteRange[1] - noteRange[0] + 1;

  let midiFileInput: HTMLInputElement;

  async function handleMidiImport(event: Event) {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (file && $projectStore) {
      const buffer = await file.arrayBuffer();
      const midi = new Midi(buffer);

      if (midi.tracks.length > 0) {
        // Just take the first track with notes for MVP
        const track = midi.tracks.find(t => t.notes.length > 0) || midi.tracks[0];

        for (const note of track.notes) {
           // Tonejs midi ticks are tied to header.ppq, we need to map to OP-XY STEP_TICKS.
           // Simplified approach for MVP: assume 1 beat = 1/4 note = 4 steps = 4 * STEP_TICKS.
           // A more robust app would calculate exactly based on BPM or PPQ.
           // Let's use PPQ mapping:
           const opXyTicksPerBeat = STEP_TICKS * 4; // Assuming 1 step = 1/16th note, 1 beat = 4 steps
           const tick = Math.round((note.ticks / midi.header.ppq) * opXyTicksPerBeat);
           const gate = Math.round((note.durationTicks / midi.header.ppq) * opXyTicksPerBeat);

           try {
             $projectStore.addNote($activeTrackStore, {
                tick,
                gate,
                note: note.midi,
                velocity: Math.floor(note.velocity * 127),
                patternIndex: $activePatternStore
             });
           } catch(e: any) {
             console.warn("Could not add note:", e.message);
           }
        }
        projectStore.set($projectStore); // Trigger reactivity
        alert(`Imported ${track.notes.length} notes into Track ${$activeTrackStore}, Pattern P${$activePatternStore + 1}.`);
      }
    }
  }

  function handleGridClick(stepIndex: number, noteValue: number) {
    if (!$projectStore) return;

    const tick = stepIndex * STEP_TICKS;
    const existingNoteIndex = notes.findIndex(n => n.tick === tick && n.note === noteValue);

    if (existingNoteIndex >= 0) {
      // Simplistic remove (we need a way to remove notes in image_writer, but for now we reconstruct)
      // Actually, removing from the encoded binary note array is tricky without rebuilding the array.
      // Let's add a `removeNote` method to ImageProject first or just not support removal for MVP
      alert("Note removal not fully implemented in byte-level codec yet. For MVP, please only add notes.");
    } else {
      try {
        $projectStore.addNote($activeTrackStore, { step: stepIndex + 1, note: noteValue, patternIndex: $activePatternStore });
        projectStore.set($projectStore); // Trigger reactivity
      } catch (e: any) {
        alert(e.message);
      }
    }
  }
</script>

<div class="flex flex-col h-full bg-neutral-900 border border-neutral-700 rounded-lg overflow-hidden">

  <!-- Toolbar -->
  <div class="flex flex-wrap justify-between items-center bg-neutral-800 p-2 border-b border-neutral-700 gap-4">
    <!-- Track Selector -->
    <div class="flex overflow-x-auto no-scrollbar">
    {#each Array(16) as _, i}
      <button
        class="flex-shrink-0 w-12 h-12 flex items-center justify-center font-bold text-lg rounded-md mx-1 transition-all cursor-pointer"
        style="
          background-color: {$activeTrackStore === i + 1 ? trackColors[i] : 'transparent'};
          color: {$activeTrackStore === i + 1 ? '#000' : trackColors[i]};
          border: 2px solid {trackColors[i]};
        "
        on:click={() => $activeTrackStore = i + 1}
      >
        {i + 1}
      </button>
    {/each}
    </div>

    <!-- Pattern Selector -->
    <div class="flex overflow-x-auto no-scrollbar bg-neutral-900 rounded-md p-1 border border-neutral-700">
      {#if $projectStore}
        {@const patternCount = $projectStore.getPatternCount($activeTrackStore)}
        {#each Array(patternCount) as _, p}
          <button
            class="flex-shrink-0 px-3 py-1 text-sm font-bold rounded mx-[2px] transition-all cursor-pointer"
            style="
              background-color: {$activePatternStore === p ? trackColors[$activeTrackStore - 1] : 'transparent'};
              color: {$activePatternStore === p ? '#000' : '#888'};
            "
            on:click={() => activePatternStore.set(p)}
          >
            P{p + 1}
          </button>
        {/each}
      {/if}
    </div>

    <!-- MIDI Import -->
    <div class="px-2">
       <input
          type="file"
          accept=".mid,.midi"
          bind:this={midiFileInput}
          on:change={handleMidiImport}
          class="hidden"
        />
        <button
          class="px-3 py-1 bg-neutral-700 hover:bg-neutral-600 rounded text-xs font-bold transition-colors uppercase tracking-wider whitespace-nowrap cursor-pointer text-neutral-300"
          on:click={() => midiFileInput.click()}
        >
          Import MIDI
        </button>
    </div>
  </div>

  <!-- Piano Roll Grid -->
  <div class="flex-1 overflow-auto relative bg-neutral-900">
    <div
      class="grid absolute top-0 left-0"
      style="grid-template-columns: repeat({steps}, minmax(30px, 1fr)); grid-template-rows: repeat({totalNotes}, 20px);"
    >
      {#each Array(totalNotes) as _, r}
        {@const noteValue = noteRange[1] - r}
        {#each Array(steps) as _, c}
          <!-- svelte-ignore a11y-click-events-have-key-events -->
          <!-- svelte-ignore a11y-no-static-element-interactions -->
          <div
            class="border-b border-r border-neutral-800/50 hover:bg-neutral-800 cursor-pointer flex items-center justify-center text-[8px] text-neutral-600"
            style="
              background-color: {
                c % 16 === 0 ? 'rgba(255,255,255,0.03)' :
                c % 4 === 0 ? 'rgba(255,255,255,0.01)' : 'transparent'
              }
            "
            on:click={() => handleGridClick(c, noteValue)}
          >
            {#if c === 0}
               <!-- Show note name on first col -->
               {noteValue}
            {/if}
          </div>
        {/each}
      {/each}

      <!-- Render Notes -->
      {#each notes as note}
         {@const stepIndex = Math.floor(note.tick / STEP_TICKS)}
         {@const rowIndex = noteRange[1] - note.note}
         {#if stepIndex < steps && rowIndex >= 0 && rowIndex < totalNotes}
            <div
              class="absolute rounded-sm pointer-events-none shadow-[0_0_8px_rgba(0,0,0,0.5)] border border-black/50"
              style="
                left: {stepIndex * 30 + 2}px;
                top: {rowIndex * 20 + 2}px;
                width: {Math.max(10, (note.gate / STEP_TICKS) * 30 - 4)}px;
                height: 16px;
                background-color: {trackColors[$activeTrackStore - 1]};
              "
            ></div>
         {/if}
      {/each}
    </div>
  </div>
</div>

<style>
  .no-scrollbar::-webkit-scrollbar {
    display: none;
  }
  .no-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
</style>
