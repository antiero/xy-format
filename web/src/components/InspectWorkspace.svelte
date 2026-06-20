<script lang="ts">
  import { SCENE_COUNT } from '../lib/xy/image_writer';
  import { display16thsAsBars } from '../lib/xy/timing';
  import type { XYProjectViewModel } from '../lib/xy/projectViewModel';

  export let project: XYProjectViewModel;

  $: activeTrack = project.tracks[project.activeTrackIndex];
  $: activePattern = activeTrack.patterns[project.activePatternIndex];
  $: activeScene = project.scenes[project.activeSceneIndex];
  $: presentSceneFlags = project.scenes
    .map((scene) => scene.present ? scene.index + 1 : null)
    .filter((value): value is number => value !== null);
  $: unknownScales = project.validation.filter((issue) => issue.code === 'track-scale-unknown' || issue.code === 'track-scale-read-only');
</script>

<section class="workspace inspect-workspace">
  <div class="workspace-head">
    <div>
      <p class="eyebrow">Inspect</p>
      <h2>Decoded project report</h2>
    </div>
    <div class="status-strip">
      <span>{project.imageProject.image.length.toLocaleString()} decoded bytes</span>
      <span>{project.imageProject.header.length} byte wrapper</span>
    </div>
  </div>

  <div class="inspect-grid">
    <section class="section-band">
      <div class="section-title">
        <span>active pattern</span>
        <span>{activeTrack.label} · P{activePattern.index + 1}</span>
      </div>
      <dl class="kv-list">
        <div><dt>steps</dt><dd>{activePattern.totalSteps} raw {activePattern.rawSteps}</dd></div>
        <div><dt>bars</dt><dd>{activePattern.bars}, final {activePattern.finalBarSteps}</dd></div>
        <div><dt>scale byte</dt><dd>0x{activePattern.trackScaleRaw.toString(16).padStart(2, '0')} · {activePattern.trackScaleLabel}</dd></div>
        <div><dt>length</dt><dd>{display16thsAsBars(activePattern.effectiveLength16ths)}</dd></div>
        <div><dt>notes</dt><dd>{activePattern.notes.length}</dd></div>
      </dl>
    </section>

    <section class="section-band">
      <div class="section-title">
        <span>active scene</span>
        <span>scene {activeScene.index + 1}</span>
      </div>
      <dl class="kv-list">
        <div><dt>present</dt><dd>{activeScene.present ? 'yes' : 'no'}</dd></div>
        <div><dt>length</dt><dd>{display16thsAsBars(activeScene.length16ths)}</dd></div>
        <div><dt>muted tracks</dt><dd>{activeScene.mutedTracks.map((muted, i) => muted ? `T${i + 1}` : '').filter(Boolean).join(', ') || 'none'}</dd></div>
        <div><dt>pattern row</dt><dd>{activeScene.patternByTrack.map((p) => `P${p + 1}`).join(' ')}</dd></div>
      </dl>
    </section>

    <section class="section-band">
      <div class="section-title">
        <span>scene flags</span>
        <span>{presentSceneFlags.length}/{SCENE_COUNT}</span>
      </div>
      <p class="mono-block">{presentSceneFlags.length ? presentSceneFlags.join(', ') : 'none'}</p>
    </section>

    <section class="section-band">
      <div class="section-title">
        <span>song footer</span>
        <span>Song 1</span>
      </div>
      <dl class="kv-list">
        <div><dt>supported</dt><dd>{project.songs[0]?.supported ? 'yes' : 'no'}</dd></div>
        <div><dt>loop</dt><dd>{project.songs[0]?.loop ? 'on' : 'off'}</dd></div>
        <div><dt>chain</dt><dd>{project.songs[0]?.sceneChain.map((scene) => scene + 1).join(' → ') || 'empty'}</dd></div>
      </dl>
    </section>

    <section class="section-band wide">
      <div class="section-title">
        <span>known partials</span>
        <span>{unknownScales.length} timing warning{unknownScales.length === 1 ? '' : 's'}</span>
      </div>
      {#if unknownScales.length === 0}
        <p class="empty-line">No unknown timing bytes in loaded patterns.</p>
      {:else}
        <div class="issue-list">
          {#each unknownScales as issue}
            <div class="issue warning">
              <span>{issue.code}</span>
              <p>{issue.message}</p>
            </div>
          {/each}
        </div>
      {/if}
    </section>

    <section class="section-band wide">
      <div class="section-title">
        <span>all validation</span>
        <span>{project.validation.length}</span>
      </div>
      {#if project.validation.length === 0}
        <p class="empty-line">No validation issues.</p>
      {:else}
        <div class="issue-list">
          {#each project.validation as issue}
            <div class="issue {issue.severity}">
              <span>{issue.severity}</span>
              <p>{issue.message}</p>
            </div>
          {/each}
        </div>
      {/if}
    </section>
  </div>
</section>
