<script lang="ts">
  import { onDestroy } from 'svelte';
  import { currentTickStore, dispatchProjectEdit, isPlayingStore, scrollXStore, scrollYStore } from '../stores/project';
  import { audioService } from '../lib/audio';
  import { STEP_TICKS } from '../lib/xy/image_writer';
  import {
    collectPlaybackEvents,
    crossesPlaybackPosition,
    playbackLoopLength16ths,
    type PlaybackEvent,
    type PlaybackScope,
  } from '../lib/xy/playback';
  import { display16thsAsBars, scaleTo16thsPerStep } from '../lib/xy/timing';
  import type { XYNoteViewModel, XYPatternViewModel, XYProjectViewModel } from '../lib/xy/projectViewModel';

  export let project: XYProjectViewModel;

  let timelineMode: 'fit' | 'global' = 'fit';
  let playbackScope: PlaybackScope = 'track';
  let pxPer16th = 34;
  let gridEl: HTMLDivElement;
  let animationFrame = 0;
  let lastFrameMs = 0;
  let lastPlaybackPosition16ths = 0;
  let transportState: 'idle' | 'loading' | 'playing' = 'idle';
  let playbackError = '';

  $: track = project.tracks[project.activeTrackIndex];
  $: pattern = track.patterns[project.activePatternIndex] ?? track.patterns[0];
  $: selectedNote = pattern.notes.find((note) => note.id === project.selectedNoteId);
  $: visibleNotes = makeVisibleNotes(pattern);
  $: playbackEvents = collectPlaybackEvents(project, playbackScope, track.index, pattern.index, project.activeSceneIndex);
  $: loopLength16ths = playbackLoopLength16ths(project, playbackScope, track.index, pattern.index, project.activeSceneIndex);
  $: timelineLength = timelineMode === 'global'
    ? Math.max(...project.tracks.flatMap((candidate) => candidate.patterns.map((p) => p.effectiveLength16ths)), pattern.effectiveLength16ths, loopLength16ths)
    : Math.max(pattern.effectiveLength16ths, loopLength16ths);
  $: rollWidth = Math.max(720, timelineLength * pxPer16th);
  $: scaleFactor = scaleTo16thsPerStep(pattern.trackScale) ?? 1;
  $: playbackProgress = loopLength16ths > 0 ? Math.min(1, $currentTickStore / loopLength16ths) : 0;
  $: playheadLeft = 58 + Math.min(timelineLength, $currentTickStore) * pxPer16th;

  function makeVisibleNotes(current: XYPatternViewModel): number[] {
    if (current.notes.length === 0) {
      return Array.from({ length: 49 }, (_, i) => 84 - i);
    }
    const pitches = current.notes.map((note) => note.note);
    const max = Math.min(108, Math.max(...pitches) + 5);
    const min = Math.max(24, Math.min(...pitches) - 5);
    return Array.from({ length: max - min + 1 }, (_, i) => max - i);
  }

  function noteName(note: number): string {
    const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    return `${names[note % 12]}${Math.floor(note / 12) - 1}`;
  }

  function noteAtStep(step: number): XYNoteViewModel | undefined {
    return pattern.notes.find((note) => note.displayStep === step);
  }

  function selectTrack(trackIndex: number) {
    stopPlayback();
    dispatchProjectEdit({ type: 'set-active-track', trackIndex });
  }

  function selectPattern(patternIndex: number) {
    stopPlayback();
    dispatchProjectEdit({ type: 'set-active-pattern', patternIndex });
  }

  function setSteps(steps: number) {
    dispatchProjectEdit({
      type: 'set-pattern-steps',
      trackIndex: track.index,
      patternIndex: pattern.index,
      steps,
    });
  }

  function setScale(scale: string) {
    dispatchProjectEdit({
      type: 'set-track-scale',
      trackIndex: track.index,
      patternIndex: pattern.index,
      scale: scale as never,
    });
  }

  function handleGridClick(event: MouseEvent) {
    if (!gridEl) return;
    const rect = gridEl.getBoundingClientRect();
    const x = event.clientX - rect.left + gridEl.scrollLeft - 58;
    const y = event.clientY - rect.top + gridEl.scrollTop;
    if (x < 0) return;
    const start16ths = Math.max(0, x / pxPer16th);
    const tick = Math.floor(start16ths / scaleFactor) * STEP_TICKS;
    const row = Math.floor(y / 22);
    const pitch = visibleNotes[row];
    if (pitch === undefined || tick >= pattern.totalSteps * STEP_TICKS) return;

    dispatchProjectEdit({
      type: 'add-note',
      trackIndex: track.index,
      patternIndex: pattern.index,
      note: {
        tick,
        gateTicks: STEP_TICKS,
        note: pitch,
        velocity: 100,
      },
    });
    void previewMidiNote(track.index, pitch, 100, STEP_TICKS);
  }

  function handleGridKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      dispatchProjectEdit({ type: 'select-note', noteId: undefined });
    }
  }

  function selectNote(event: MouseEvent, note: XYNoteViewModel) {
    event.stopPropagation();
    dispatchProjectEdit({ type: 'select-note', noteId: note.id });
    void previewMidiNote(track.index, note.note, note.velocity, Math.min(note.gateTicks, STEP_TICKS * 2));
  }

  function updateSelected(patch: Partial<XYNoteViewModel>) {
    if (!selectedNote) return;
    dispatchProjectEdit({
      type: 'update-note',
      trackIndex: track.index,
      patternIndex: pattern.index,
      noteId: selectedNote.id,
      patch,
    });
  }

  function deleteSelected() {
    if (!selectedNote) return;
    dispatchProjectEdit({
      type: 'delete-note',
      trackIndex: track.index,
      patternIndex: pattern.index,
      noteId: selectedNote.id,
    });
  }

  function handleScroll(event: Event) {
    const target = event.target as HTMLDivElement;
    scrollXStore.set(target.scrollLeft);
    scrollYStore.set(target.scrollTop);
  }

  function msPer16th(): number {
    return 15000 / Math.max(10, project.tempoBpm || 120);
  }

  async function previewMidiNote(trackIndex: number, note: number, velocity = 100, gateTicks = STEP_TICKS) {
    playbackError = '';
    try {
      await audioService.ensureReady();
      const factor = scaleTo16thsPerStep(pattern.trackScale) ?? 1;
      const durationMs = Math.max(60, (gateTicks / STEP_TICKS) * factor * msPer16th());
      audioService.noteOn(trackIndex, note, velocity);
      audioService.noteOff(trackIndex, note, durationMs);
    } catch (error) {
      playbackError = error instanceof Error ? error.message : 'audio unavailable';
    }
  }

  function schedulePlaybackEvent(event: PlaybackEvent) {
    const durationMs = Math.max(30, event.duration16ths * msPer16th());
    audioService.noteOn(event.trackIndex, event.note, event.velocity);
    audioService.noteOff(event.trackIndex, event.note, durationMs);
  }

  function playbackFrame(now: number) {
    if (!$isPlayingStore || loopLength16ths <= 0) return;
    if (!lastFrameMs) lastFrameMs = now;

    const delta16ths = (now - lastFrameMs) / msPer16th();
    lastFrameMs = now;

    const previous = lastPlaybackPosition16ths;
    let next = previous + delta16ths;
    const didWrap = next >= loopLength16ths;
    if (didWrap) {
      next %= loopLength16ths;
      audioService.stopAll();
    }

    for (const event of playbackEvents) {
      if (crossesPlaybackPosition(event.start16ths, previous, next, didWrap)) {
        schedulePlaybackEvent(event);
      }
    }

    lastPlaybackPosition16ths = next;
    currentTickStore.set(next);
    animationFrame = requestAnimationFrame(playbackFrame);
  }

  async function togglePlayback() {
    if ($isPlayingStore) {
      stopPlayback();
      return;
    }

    playbackError = '';
    transportState = 'loading';
    try {
      await audioService.ensureReady();
      lastPlaybackPosition16ths = $currentTickStore >= loopLength16ths ? 0 : $currentTickStore;
      lastFrameMs = performance.now();
      isPlayingStore.set(true);
      transportState = 'playing';
      animationFrame = requestAnimationFrame(playbackFrame);
    } catch (error) {
      transportState = 'idle';
      isPlayingStore.set(false);
      playbackError = error instanceof Error ? error.message : 'audio unavailable';
    }
  }

  function stopPlayback() {
    if (animationFrame) {
      cancelAnimationFrame(animationFrame);
      animationFrame = 0;
    }
    audioService.stopAll();
    isPlayingStore.set(false);
    transportState = 'idle';
    lastFrameMs = 0;
  }

  function rewindPlayback() {
    stopPlayback();
    lastPlaybackPosition16ths = 0;
    currentTickStore.set(0);
  }

  function setPlaybackScope(scope: PlaybackScope) {
    playbackScope = scope;
    rewindPlayback();
  }

  onDestroy(() => {
    stopPlayback();
  });
</script>

<section class="workspace pattern-workspace">
  <div class="workspace-head">
    <div>
      <p class="eyebrow">Pattern</p>
      <h2>{track.label} · P{pattern.index + 1}</h2>
    </div>
    <div class="status-strip">
      <span>{pattern.totalSteps} steps</span>
      <span>scale {pattern.trackScaleLabel}</span>
      <span>{display16thsAsBars(pattern.effectiveLength16ths)}</span>
    </div>
  </div>

  <div class="editor-layout">
    <aside class="side-rail">
      <div class="rail-section">
        <span class="rail-label">tracks</span>
        <div class="track-pad-grid">
          {#each project.tracks as candidate}
            <button
              class="pad-button"
              class:active={candidate.index === track.index}
              class:red={candidate.colorRole === 'red'}
              type="button"
              on:click={() => selectTrack(candidate.index)}
            >
              {candidate.label}
            </button>
          {/each}
        </div>
      </div>

      <div class="rail-section">
        <span class="rail-label">patterns</span>
        <div class="pattern-pad-grid">
          {#each track.patterns as candidate}
            <button
              class="pad-button"
              class:active={candidate.index === pattern.index}
              type="button"
              on:click={() => selectPattern(candidate.index)}
            >
              P{candidate.index + 1}
            </button>
          {/each}
        </div>
      </div>

      <div class="rail-section">
        <span class="rail-label">length</span>
        <label class="field-label">
          steps
          <input type="number" min="1" max="64" value={pattern.totalSteps} on:change={(event) => setSteps(Number((event.target as HTMLInputElement).value))} />
        </label>
        <div class="quick-row">
          {#each [16, 32, 48, 64] as steps}
            <button type="button" class:active={pattern.totalSteps === steps} on:click={() => setSteps(steps)}>{steps / 16}b</button>
          {/each}
        </div>
      </div>

      <div class="rail-section">
        <span class="rail-label">scale</span>
        <div class="scale-grid">
          {#each ['1/2', '1', '2', '3', '4', '6', '8', '16'] as scale}
            <button
              type="button"
              class:active={pattern.trackScale === scale}
              disabled={!['1/2', '1', '2', '16'].includes(scale)}
              title={['1/2', '1', '2', '16'].includes(scale) ? `set scale ${scale}` : `scale ${scale} is read-only until device write tests exist`}
              on:click={() => setScale(scale)}
            >
              {scale}
            </button>
          {/each}
        </div>
      </div>
    </aside>

    <div class="pattern-main">
      <div class="step-panel">
        <div class="section-title">
          <span>OP-XY step view</span>
          <span>{pattern.bars} bar{pattern.bars === 1 ? '' : 's'} · final {pattern.finalBarSteps}</span>
        </div>
        <div class="bar-pages" style={`grid-template-columns: repeat(${pattern.bars}, minmax(170px, 1fr));`}>
          {#each Array(pattern.bars) as _, barIndex}
            <div class="bar-page" class:partial={barIndex === pattern.bars - 1 && pattern.finalBarSteps < 16}>
              <span class="bar-label">bar {barIndex + 1}</span>
              <div class="step-leds">
                {#each Array(16) as _, stepInBar}
                  {@const step = barIndex * 16 + stepInBar}
                  {@const active = step < pattern.totalSteps}
                  {@const note = noteAtStep(step)}
                  <button
                    type="button"
                    class="step-led"
                    class:on={Boolean(note)}
                    class:inactive={!active}
                    class:selected={note && note.id === project.selectedNoteId}
                    disabled={!active}
                    on:click={() => note && dispatchProjectEdit({ type: 'select-note', noteId: note.id })}
                  >
                    {stepInBar + 1}
                  </button>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      </div>

      <div class="transport-panel">
        <div class="transport-controls">
          <button
            type="button"
            class="transport-play"
            class:active={$isPlayingStore}
            disabled={transportState === 'loading' || playbackEvents.length === 0}
            on:click={togglePlayback}
          >
            {$isPlayingStore ? 'stop' : transportState === 'loading' ? 'load' : 'play'}
          </button>
          <button type="button" on:click={rewindPlayback}>rew</button>
          <div class="segmented tight">
            <button type="button" class:active={playbackScope === 'track'} on:click={() => setPlaybackScope('track')}>track</button>
            <button type="button" class:active={playbackScope === 'scene'} on:click={() => setPlaybackScope('scene')}>scene</button>
          </div>
        </div>
        <div class="transport-readout">
          <span>{project.tempoBpm.toFixed(1)} bpm</span>
          <span>{playbackEvents.length} note{playbackEvents.length === 1 ? '' : 's'}</span>
          <span>{display16thsAsBars(loopLength16ths)}</span>
        </div>
        <div class="transport-meter" aria-hidden="true">
          <span style={`width: ${playbackProgress * 100}%;`}></span>
        </div>
        {#if playbackError}
          <span class="transport-error">{playbackError}</span>
        {/if}
      </div>

      <div class="roll-toolbar">
        <div class="segmented">
          <button type="button" class:active={timelineMode === 'fit'} on:click={() => timelineMode = 'fit'}>fit pattern</button>
          <button type="button" class:active={timelineMode === 'global'} on:click={() => timelineMode = 'global'}>global time</button>
        </div>
        <label class="inline-range">
          zoom
          <input type="range" min="18" max="72" step="2" bind:value={pxPer16th} />
        </label>
      </div>

      <div class="piano-roll" bind:this={gridEl} on:scroll={handleScroll}>
        <div
          class="roll-canvas"
          style={`width: ${rollWidth + 58}px; height: ${visibleNotes.length * 22}px;`}
          role="grid"
          tabindex="0"
          aria-label="Piano roll note grid"
          on:click={handleGridClick}
          on:keydown={handleGridKeydown}
        >
          <div class="key-column">
            {#each visibleNotes as midi}
              <div class="key-label">{noteName(midi)}</div>
            {/each}
          </div>
          <div
            class="roll-grid"
            style={`left: 58px; width: ${rollWidth}px; height: ${visibleNotes.length * 22}px; background-size: ${pxPer16th * 4}px 22px, ${pxPer16th}px 22px;`}
          ></div>
          {#each Array(Math.ceil(timelineLength / 16)) as _, bar}
            <div class="bar-marker" style={`left: ${58 + bar * 16 * pxPer16th}px;`}>B{bar + 1}</div>
          {/each}
          <div
            class="playhead"
            class:active={$isPlayingStore || $currentTickStore > 0}
            style={`left: ${playheadLeft}px; height: ${visibleNotes.length * 22}px;`}
          ></div>
          {#each pattern.notes as note}
            {@const row = visibleNotes.indexOf(note.note)}
            {#if row >= 0}
              <button
                class="roll-note"
                class:selected={note.id === project.selectedNoteId}
                style={`left: ${58 + note.start16ths * pxPer16th}px; top: ${row * 22 + 2}px; width: ${Math.max(6, note.duration16ths * pxPer16th - 2)}px;`}
                type="button"
                aria-label={`${note.noteName} at step ${note.displayStep + 1}`}
                title={`${note.noteName} · step ${note.displayStep + 1}`}
                on:click={(event) => selectNote(event, note)}
              >
                <span style={`height: ${Math.max(0, 100 - (note.velocity / 127) * 100)}%;`}></span>
              </button>
            {/if}
          {/each}
        </div>
      </div>
    </div>

    <aside class="inspector">
      <div class="section-title">
        <span>note</span>
        <span>{selectedNote ? selectedNote.noteName : 'none'}</span>
      </div>
      {#if selectedNote}
        <label class="field-label">
          pitch
          <input type="number" min="0" max="127" value={selectedNote.note} on:change={(event) => updateSelected({ note: Number((event.target as HTMLInputElement).value) })} />
        </label>
        <label class="field-label">
          step
          <input type="number" min="1" max={pattern.totalSteps} value={selectedNote.displayStep + 1} on:change={(event) => updateSelected({ tick: (Number((event.target as HTMLInputElement).value) - 1) * STEP_TICKS })} />
        </label>
        <label class="field-label">
          gate
          <input type="number" min="1" max="64" step="0.25" value={selectedNote.gateTicks / STEP_TICKS} on:change={(event) => updateSelected({ gateTicks: Number((event.target as HTMLInputElement).value) * STEP_TICKS })} />
        </label>
        <label class="field-label">
          velocity
          <input type="number" min="1" max="127" value={selectedNote.velocity} on:change={(event) => updateSelected({ velocity: Number((event.target as HTMLInputElement).value) })} />
        </label>
        <button class="secondary-button" type="button" on:click={() => previewMidiNote(track.index, selectedNote.note, selectedNote.velocity, selectedNote.gateTicks)}>audition</button>
        <button class="danger-button" type="button" on:click={deleteSelected}>delete note</button>
      {:else}
        <p class="empty-line">Click the roll to add a note, or select an existing note.</p>
      {/if}
    </aside>
  </div>
</section>
