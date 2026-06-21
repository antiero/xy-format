<script lang="ts">
  import { activeModeStore, dispatchProjectEdit } from "../stores/project";
  import { display16thsAsBars } from "../lib/xy/timing";
  import {
    projectPatternDataCount,
    projectSummary,
    projectTracksWithStepData,
    patternHasStepData,
    trackPatternDataCount,
    type XYProjectViewModel,
  } from "../lib/xy/projectViewModel";
  import { validationCounts } from "../lib/xy/validation";

  export let project: XYProjectViewModel;

  $: counts = validationCounts(project.validation);
  $: presentScenes = project.scenes.filter((scene) => scene.present);
  $: longestScene = presentScenes.reduce(
    (max, scene) => Math.max(max, scene.length16ths),
    0,
  );
  $: activeTracks = projectTracksWithStepData(project);
  $: activePatternCount = projectPatternDataCount(project);

  function openTrack(trackIndex: number) {
    dispatchProjectEdit({ type: "set-active-track", trackIndex });
    activeModeStore.set("pattern");
  }
</script>

<section class="workspace project-workspace">
  <div class="workspace-head">
    <div>
      <p class="eyebrow">Project</p>
      <h2>{project.fileName}</h2>
    </div>
    <div class="status-strip">
      <span
        class:status-bad={counts.errors > 0}
        class:status-warn={counts.errors === 0 && counts.warnings > 0}
      >
        {counts.errors} errors · {counts.warnings} warnings
      </span>
      <span>{project.modified ? "modified" : "clean"}</span>
    </div>
  </div>

  <div class="summary-grid">
    <div class="metric">
      <span class="metric-value">{activeTracks.length}</span>
      <span class="metric-label">active tracks</span>
    </div>
    <div class="metric">
      <span class="metric-value">{activePatternCount}</span>
      <span class="metric-label">patterns with data</span>
    </div>
    <div class="metric">
      <span class="metric-value">{presentScenes.length}</span>
      <span class="metric-label">scenes</span>
    </div>
    <div class="metric">
      <span class="metric-value">{display16thsAsBars(longestScene)}</span>
      <span class="metric-label">longest scene</span>
    </div>
  </div>

  <div class="section-band">
    <div class="section-title">
      <span>Project map</span>
      <span>{projectSummary(project)}</span>
    </div>
    {#if activeTracks.length === 0}
      <p class="empty-line">No step data found in this project.</p>
    {:else}
      <div class="track-overview">
        {#each activeTracks as track}
          {@const patternCount = trackPatternDataCount(track)}
          {@const firstDataPattern =
            track.patterns.find(patternHasStepData) ?? track.patterns[0]}
          <button
            class="track-row"
            type="button"
            on:click={() => openTrack(track.index)}
          >
            <span class="track-led" class:red={track.colorRole === "red"}
            ></span>
            <span class="track-name">{track.label}</span>
            <span>{track.kind}</span>
            <span>{patternCount} pattern{patternCount === 1 ? "" : "s"}</span>
            <span>{firstDataPattern?.trackScaleLabel ?? "scale ?"}</span>
          </button>
        {/each}
      </div>
    {/if}
  </div>

  <div class="section-band">
    <div class="section-title">
      <span>Validation</span>
      <span
        >{project.validation.length} issue{project.validation.length === 1
          ? ""
          : "s"}</span
      >
    </div>
    {#if project.validation.length === 0}
      <p class="empty-line">No validation issues in decoded editable fields.</p>
    {:else}
      <div class="issue-list">
        {#each project.validation.slice(0, 12) as issue}
          <div class="issue {issue.severity}">
            <span>{issue.severity}</span>
            <p>{issue.message}</p>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</section>
