<script lang="ts">
  import { projectStore } from './stores/project';
  import { ImageProject } from './lib/xy/image_writer';
  import Sequencer from './components/Sequencer.svelte';
  import Arranger from './components/Arranger.svelte';

  let fileInput: HTMLInputElement;
  let activeTab: 'sequencer' | 'arranger' = 'sequencer';

  async function handleFileUpload(event: Event) {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (file) {
      const buffer = await file.arrayBuffer();
      const uint8Array = new Uint8Array(buffer);
      try {
        const proj = ImageProject.fromBytes(uint8Array);
        projectStore.set(proj);
      } catch (err) {
        console.error("Failed to parse project file:", err);
        alert("Failed to parse project file. Is it a valid .xy file?");
      }
    }
  }

  function handleDownload() {
    if (!$projectStore) return;

    try {
      const bytes = $projectStore.toBytes();
      const blob = new Blob([bytes as BlobPart], { type: 'application/octet-stream' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'edited_project.xy';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to generate project file:", err);
      alert("Failed to generate project file.");
    }
  }
</script>

<main class="min-h-screen bg-neutral-900 text-neutral-200 flex flex-col font-mono">
  <header class="bg-neutral-800 p-4 flex justify-between items-center border-b border-neutral-700">
    <div class="flex items-center gap-4">
      <h1 class="text-xl font-bold tracking-widest uppercase text-white">OP-XY Editor</h1>
      <span class="text-xs px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded-full border border-yellow-500/30">MVP</span>
    </div>

    <div class="flex items-center gap-4">
      <input
        type="file"
        accept=".xy"
        bind:this={fileInput}
        on:change={handleFileUpload}
        class="hidden"
      />
      <button
        class="px-4 py-2 bg-neutral-700 hover:bg-neutral-600 rounded text-sm transition-colors uppercase tracking-wider cursor-pointer"
        on:click={() => fileInput.click()}
      >
        Load .xy
      </button>

      {#if $projectStore}
        <button
          class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded text-sm text-white font-bold transition-colors uppercase tracking-wider shadow-lg shadow-emerald-900/50 cursor-pointer"
          on:click={handleDownload}
        >
          Save .xy
        </button>
      {/if}
    </div>
  </header>

  <div class="flex-1 p-6 flex flex-col">
    {#if !$projectStore}
      <div class="h-full flex-1 flex flex-col items-center justify-center text-neutral-500 border-2 border-dashed border-neutral-700 rounded-xl p-12 bg-neutral-800/50">
        <svg class="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
        <p class="text-lg">Please load an OP-XY project file to begin.</p>
        <p class="text-sm mt-2 opacity-75">You can find .xy files on your device's disk.</p>

        <button
          class="mt-6 px-6 py-3 bg-neutral-700 hover:bg-neutral-600 rounded-lg text-sm transition-colors uppercase tracking-wider border border-neutral-600 hover:border-neutral-500 cursor-pointer"
          on:click={() => fileInput.click()}
        >
          Browse Files
        </button>
      </div>
    {:else}
      <div class="flex gap-2 mb-4">
        <button
          class="px-6 py-2 rounded-t-lg font-bold text-sm tracking-widest uppercase transition-colors cursor-pointer {activeTab === 'sequencer' ? 'bg-neutral-800 text-white border-t border-l border-r border-neutral-700' : 'bg-neutral-900 text-neutral-500 hover:text-neutral-300'}"
          on:click={() => activeTab = 'sequencer'}
        >
          Sequencer
        </button>
        <button
          class="px-6 py-2 rounded-t-lg font-bold text-sm tracking-widest uppercase transition-colors cursor-pointer {activeTab === 'arranger' ? 'bg-neutral-800 text-white border-t border-l border-r border-neutral-700' : 'bg-neutral-900 text-neutral-500 hover:text-neutral-300'}"
          on:click={() => activeTab = 'arranger'}
        >
          Arranger
        </button>
      </div>
      <div class="bg-neutral-800 rounded-b-xl rounded-tr-xl border border-neutral-700 p-4 shadow-xl flex-1 flex flex-col min-h-0 -mt-4 z-10 relative">
        {#if activeTab === 'sequencer'}
          <Sequencer />
        {:else}
          <Arranger />
        {/if}
      </div>
    {/if}
  </div>
</main>
