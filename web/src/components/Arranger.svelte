<script lang="ts">
  import { projectStore } from '../stores/project';

  // Track colors mimicking TE aesthetic
  const trackColors = [
    '#ff3b30', '#ff9500', '#ffcc00', '#4cd964',
    '#5ac8fa', '#007aff', '#5856d6', '#ff2d55',
    '#ff3b30', '#ff9500', '#ffcc00', '#4cd964',
    '#5ac8fa', '#007aff', '#5856d6', '#ff2d55'
  ];

  const totalScenes = 99;
  const totalTracks = 16;

  // sceneGrid[sceneIndex][trackIndex] = patternId
  let sceneGrid: number[][] = Array(totalScenes).fill(0).map(() => Array(totalTracks).fill(0));

  $: if ($projectStore) {
    try {
        for (let s = 0; s < totalScenes; s++) {
            for (let t = 0; t < totalTracks; t++) {
                sceneGrid[s][t] = $projectStore.getScenePattern(s, t + 1);
            }
        }
    } catch(e) {
        console.error("Failed to parse scene grid", e);
    }
  }

  function handlePatternChange(scene: number, track: number, delta: number) {
      if (!$projectStore) return;

      let currentPattern = sceneGrid[scene][track];
      // Basic bound checking: max 9 patterns per track usually
      let newPattern = Math.max(0, Math.min(9, currentPattern + delta));

      try {
          $projectStore.setScenePattern(scene, track + 1, newPattern);
          projectStore.set($projectStore); // trigger reactivity
      } catch (e: any) {
          alert(e.message);
      }
  }

</script>

<div class="flex flex-col h-full bg-neutral-900 border border-neutral-700 rounded-lg overflow-hidden">

  <div class="bg-neutral-800 p-2 border-b border-neutral-700 flex justify-between items-center">
      <h3 class="text-sm font-bold text-neutral-300 tracking-widest uppercase">Arranger</h3>
      <div class="text-xs text-neutral-500">Scroll vertically to see all 99 scenes. Scroll horizontally for tracks.</div>
  </div>

  <div class="flex-1 overflow-auto relative bg-neutral-900">

      <table class="w-full text-xs text-left border-collapse">
          <thead class="sticky top-0 bg-neutral-800 z-10 shadow-md">
              <tr>
                  <th class="p-2 border-r border-neutral-700 w-16 text-center text-neutral-500 font-normal">Scene</th>
                  {#each Array(totalTracks) as _, t}
                     <th
                        class="p-2 border-r border-neutral-700 w-16 text-center"
                        style="color: {trackColors[t]}"
                     >
                        T{t + 1}
                     </th>
                  {/each}
              </tr>
          </thead>
          <tbody>
              {#each Array(totalScenes) as _, s}
                  <tr class="border-b border-neutral-800 hover:bg-neutral-800/50 transition-colors">
                      <td class="p-2 border-r border-neutral-700 text-center font-bold text-neutral-400">
                          {s + 1}
                      </td>
                      {#each Array(totalTracks) as _, t}
                          {@const patternId = sceneGrid[s][t]}
                          <td class="p-1 border-r border-neutral-800/50 text-center relative group">
                              <div
                                  class="w-full h-8 rounded-sm flex items-center justify-center font-bold transition-all border border-transparent hover:border-white/20"
                                  style="
                                    background-color: {patternId > 0 ? trackColors[t] : 'rgba(255,255,255,0.02)'};
                                    color: {patternId > 0 ? '#000' : 'rgba(255,255,255,0.2)'};
                                    opacity: {patternId > 0 ? 1 : 0.5};
                                  "
                              >
                                  {patternId > 0 ? `P${patternId}` : '-'}
                              </div>

                              <!-- Controls -->
                              <div class="absolute inset-0 flex flex-col justify-between opacity-0 group-hover:opacity-100 transition-opacity p-1">
                                  <button class="bg-black/50 hover:bg-white text-white hover:text-black rounded text-[8px] h-3 leading-none cursor-pointer" on:click={() => handlePatternChange(s, t, 1)}>▲</button>
                                  <button class="bg-black/50 hover:bg-white text-white hover:text-black rounded text-[8px] h-3 leading-none cursor-pointer" on:click={() => handlePatternChange(s, t, -1)}>▼</button>
                              </div>
                          </td>
                      {/each}
                  </tr>
              {/each}
          </tbody>
      </table>

  </div>

</div>
