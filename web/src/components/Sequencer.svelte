<script lang="ts">
  import { projectStore, activeTrackStore, activePatternStore, isPlayingStore, scrollYStore, scrollXStore, currentTickStore } from '../stores/project';
  import { STEP_TICKS } from '../lib/xy/image_writer';
  import { Midi } from '@tonejs/midi';
  import { audioService } from '../lib/audio';
  import { onMount, onDestroy } from 'svelte';

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

  // Define grid layout similar to Signal
  const KEY_WIDTH = 64;
  const ROW_HEIGHT = 20;
  const BEAT_WIDTH = 120; // 4 steps per beat
  const TICK_WIDTH = BEAT_WIDTH / (STEP_TICKS * 4);
  const noteRange = [24, 108]; // C1 to C8 roughly
  const totalNotes = noteRange[1] - noteRange[0] + 1;
  const steps = 64;
  const totalTicks = steps * STEP_TICKS;

  let gridContainer: HTMLDivElement;

  function isBlackKey(note: number) {
      const n = note % 12;
      return n === 1 || n === 3 || n === 6 || n === 8 || n === 10;
  }

  function getNoteName(note: number) {
      const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
      const name = notes[note % 12];
      const octave = Math.floor(note / 12) - 1;
      return `${name}${octave}`;
  }

  let midiFileInput: HTMLInputElement;

  async function handleMidiImport(event: Event) {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (file && $projectStore) {
      const buffer = await file.arrayBuffer();
      const midi = new Midi(buffer);

      if (midi.tracks.length > 0) {
        const track = midi.tracks.find(t => t.notes.length > 0) || midi.tracks[0];

        for (const note of track.notes) {
           const opXyTicksPerBeat = STEP_TICKS * 4;
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
        projectStore.set($projectStore);
        alert(`Imported ${track.notes.length} notes into Track ${$activeTrackStore}, Pattern P${$activePatternStore + 1}.`);
      }
    }
  }

  function handleGridClick(e: MouseEvent) {
    if (!$projectStore) return;

    const rect = gridContainer.getBoundingClientRect();
    const x = e.clientX - rect.left + gridContainer.scrollLeft - KEY_WIDTH;
    const y = e.clientY - rect.top + gridContainer.scrollTop;

    if (x < 0) return; // Clicked on keyboard

    const tick = Math.max(0, Math.round(x / TICK_WIDTH));
    const rowIndex = Math.floor(y / ROW_HEIGHT);
    const noteValue = noteRange[1] - rowIndex;

    // Snap to 16th note (STEP_TICKS)
    const snappedTick = Math.floor(tick / STEP_TICKS) * STEP_TICKS;

    // Check if clicked on an existing note
    const existingNoteIndex = notes.findIndex(n =>
        n.note === noteValue &&
        snappedTick >= n.tick &&
        snappedTick < n.tick + n.gate
    );

    if (existingNoteIndex >= 0) {
        alert("Note removal not fully implemented in byte-level codec yet. For MVP, please only add notes.");
    } else {
        try {
            $projectStore.addNote($activeTrackStore, {
                tick: snappedTick,
                gate: STEP_TICKS, // Default 1 step gate
                note: noteValue,
                velocity: 100,
                patternIndex: $activePatternStore
            });
            projectStore.set($projectStore);

            // Preview sound
            audioService.ensureReady().then(() => {
                audioService.noteOn($activeTrackStore - 1, noteValue, 100);
                setTimeout(() => audioService.noteOff($activeTrackStore - 1, noteValue), 200);
            });
        } catch (err: any) {
            alert(err.message);
        }
    }
  }

  function playKey(noteValue: number) {
      audioService.ensureReady().then(() => {
          audioService.noteOn($activeTrackStore - 1, noteValue, 100);
      });
  }

  function stopKey(noteValue: number) {
      audioService.ensureReady().then(() => {
          audioService.noteOff($activeTrackStore - 1, noteValue);
      });
  }

  function handleScroll(e: Event) {
      const target = e.target as HTMLDivElement;
      scrollYStore.set(target.scrollTop);
      scrollXStore.set(target.scrollLeft);
  }

  let animationFrame: number;
  let lastTime: number = 0;

  // Keep track of notes currently playing
  let playingNotes = new Set<string>();

  function playLoop() {
      if (!$isPlayingStore) return;

      const now = performance.now();
      const dtMs = now - lastTime;
      lastTime = now;

      // Calculate ticks based on 120 BPM for now
      // 120 BPM = 2 beats per second = 2 * (4 * STEP_TICKS) = 8 * STEP_TICKS ticks per second
      const ticksPerSecond = 8 * STEP_TICKS;
      const ticksPerMs = ticksPerSecond / 1000;

      const oldTick = $currentTickStore;
      let newTick = oldTick + (dtMs * ticksPerMs);
      let didLoop = false;

      if (newTick > totalTicks) {
          newTick = newTick % totalTicks; // loop smoothly
          didLoop = true;
          audioService.stopAll();
          playingNotes.clear();
      }

      // Check for notes to start playing
      if ($projectStore) {
        for (let track = 1; track <= 16; track++) {
          try {
            const trackNotes = $projectStore.getNotes(track, $activePatternStore);
            for (const note of trackNotes) {
                const noteId = `${track}-${note.note}-${note.tick}`;

                // If the playhead just crossed the note start
                const isCrossedNormal = !didLoop && note.tick >= oldTick && note.tick < newTick;
                const isCrossedLoop = didLoop && (note.tick >= oldTick || note.tick < newTick);

                if ((isCrossedNormal || isCrossedLoop) && !playingNotes.has(noteId)) {
                    // note.velocity might be undefined in old saved files if not set
                    const velocity = note.velocity || 100;
                    audioService.noteOn(track - 1, note.note, velocity);
                    playingNotes.add(noteId);

                    // Schedule note off
                    const gateMs = (note.gate / ticksPerMs);
                    setTimeout(() => {
                        audioService.noteOff(track - 1, note.note);
                        playingNotes.delete(noteId);
                    }, gateMs);
                }
            }
          } catch(e) {
            // Ignore if pattern empty
          }
        }
      }

      currentTickStore.set(newTick);

      animationFrame = requestAnimationFrame(playLoop);
  }

  function togglePlay() {
      audioService.ensureReady().then(() => {
          isPlayingStore.update(p => !p);
          if ($isPlayingStore) {
              lastTime = performance.now();
              playLoop();
          } else {
              cancelAnimationFrame(animationFrame);
              audioService.stopAll();
          }
      });
  }

  onDestroy(() => {
      cancelAnimationFrame(animationFrame);
      audioService.stopAll();
  });

</script>

<div class="flex flex-col h-full bg-[#1e1e1e] border border-neutral-700 rounded-lg overflow-hidden select-none">

  <!-- Toolbar -->
  <div class="flex flex-wrap justify-between items-center bg-[#252526] p-2 border-b border-neutral-700 gap-4">
    <!-- Playback Controls -->
    <div class="flex gap-2">
        <button
            class="px-4 py-1 rounded font-bold text-sm tracking-widest uppercase transition-colors { $isPlayingStore ? 'bg-emerald-600 text-white' : 'bg-neutral-700 text-neutral-300 hover:bg-neutral-600' }"
            on:click={togglePlay}
        >
            {$isPlayingStore ? 'Stop' : 'Play'}
        </button>
    </div>

    <!-- Track Selector -->
    <div class="flex overflow-x-auto no-scrollbar">
    {#each Array(16) as _, i}
      <button
        class="flex-shrink-0 w-8 h-8 flex items-center justify-center font-bold text-xs rounded-md mx-[2px] transition-all cursor-pointer"
        style="
          background-color: {$activeTrackStore === i + 1 ? trackColors[i] : 'transparent'};
          color: {$activeTrackStore === i + 1 ? '#000' : trackColors[i]};
          border: 1px solid {trackColors[i]};
        "
        on:click={() => $activeTrackStore = i + 1}
      >
        T{i + 1}
      </button>
    {/each}
    </div>

    <!-- Pattern Selector -->
    <div class="flex overflow-x-auto no-scrollbar bg-neutral-900 rounded-md p-1 border border-neutral-700">
      {#if $projectStore}
        {@const patternCount = $projectStore.getPatternCount($activeTrackStore)}
        {#each Array(patternCount) as _, p}
          <button
            class="flex-shrink-0 px-3 py-1 text-xs font-bold rounded mx-[2px] transition-all cursor-pointer"
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

  <!-- Piano Roll Area -->
  <div class="flex-1 overflow-auto relative bg-[#1e1e1e]" bind:this={gridContainer} on:scroll={handleScroll}>
    <div
        class="relative"
        style="width: {KEY_WIDTH + totalTicks * TICK_WIDTH}px; height: {totalNotes * ROW_HEIGHT}px;"
    >
      <!-- Background Grid -->
      <div
          class="absolute top-0 bottom-0 pointer-events-none"
          style="left: {KEY_WIDTH}px; right: 0; background-size: {BEAT_WIDTH}px {ROW_HEIGHT}px; background-image: linear-gradient(to right, #333 1px, transparent 1px), linear-gradient(to bottom, #2a2a2a 1px, transparent 1px);"
      >
          <!-- Minor beat grid -->
          <div class="absolute inset-0" style="background-size: {BEAT_WIDTH/4}px {ROW_HEIGHT}px; background-image: linear-gradient(to right, #2a2a2a 1px, transparent 1px);"></div>
      </div>

      <!-- Horizontal row highlights for black keys -->
      <div class="absolute top-0 bottom-0 pointer-events-none z-0" style="left: {KEY_WIDTH}px; right: 0;">
          {#each Array(totalNotes) as _, r}
              {@const noteValue = noteRange[1] - r}
              {#if isBlackKey(noteValue)}
                  <div class="absolute w-full opacity-5" style="top: {r * ROW_HEIGHT}px; height: {ROW_HEIGHT}px; background-color: #000;"></div>
              {/if}
          {/each}
      </div>

      <!-- Playhead -->
      <div class="absolute top-0 bottom-0 w-[2px] bg-emerald-500 z-20 pointer-events-none shadow-[0_0_8px_#10b981]" style="left: {KEY_WIDTH + $currentTickStore * TICK_WIDTH}px;"></div>

      <!-- Interactive Grid Layer -->
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <!-- svelte-ignore a11y-no-static-element-interactions -->
      <div class="absolute inset-0 z-10 cursor-crosshair" on:click={handleGridClick}>
          <!-- Render Notes -->
          {#each notes as note}
            {@const tickStart = note.tick}
            {@const rowIndex = noteRange[1] - note.note}
            {#if tickStart < totalTicks && rowIndex >= 0 && rowIndex < totalNotes}
                <div
                class="absolute rounded-sm shadow-[0_0_8px_rgba(0,0,0,0.5)] border border-black/50 hover:brightness-125 transition-all overflow-hidden"
                style="
                    left: {KEY_WIDTH + tickStart * TICK_WIDTH}px;
                    top: {rowIndex * ROW_HEIGHT + 1}px;
                    width: {note.gate * TICK_WIDTH - 1}px;
                    height: {ROW_HEIGHT - 2}px;
                    background-color: {trackColors[$activeTrackStore - 1]};
                "
                >
                    <!-- Velocity indicator overlay -->
                    <div class="absolute bottom-0 left-0 right-0 bg-black/20" style="height: {(1 - note.velocity/127) * 100}%"></div>
                </div>
            {/if}
          {/each}
      </div>

      <!-- Keyboard Sidebar (Sticky) -->
      <div class="absolute top-0 bottom-0 left-0 bg-[#1e1e1e] border-r border-neutral-700 z-30" style="width: {KEY_WIDTH}px; transform: translateX({$scrollXStore}px);">
          {#each Array(totalNotes) as _, r}
              {@const noteValue = noteRange[1] - r}
              {@const isBlack = isBlackKey(noteValue)}
              {@const noteName = getNoteName(noteValue)}
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <div
                  class="absolute w-full border-b border-neutral-800 flex items-center justify-end pr-2 text-[10px] font-mono cursor-pointer hover:opacity-80 active:opacity-100"
                  style="
                      top: {r * ROW_HEIGHT}px;
                      height: {ROW_HEIGHT}px;
                      background-color: {isBlack ? '#2d2d2d' : '#e0e0e0'};
                      color: {isBlack ? '#888' : '#333'};
                  "
                  on:mousedown={() => playKey(noteValue)}
                  on:mouseup={() => stopKey(noteValue)}
                  on:mouseleave={() => stopKey(noteValue)}
              >
                  {#if noteName.includes('C') && !noteName.includes('#')}
                      <span class="font-bold opacity-50">{noteName}</span>
                  {/if}
              </div>
          {/each}
      </div>

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