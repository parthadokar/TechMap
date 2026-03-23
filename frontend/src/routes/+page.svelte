<script>
  import { onMount } from 'svelte';
  import { companies, filtered, selectedId, loading, error } from '$lib/stores/companies';
  import FilterBar from '$lib/components/FilterBar.svelte';
  import CompanyCard from '$lib/components/CompanyCard.svelte';
  import Map from '$lib/components/Map.svelte';
  import CitySearch from '$lib/components/CitySearch.svelte';

  import '../app.css';

  export let data;  // populated by +page.js load function

  const API = 'http://localhost:8000';

  let listEl;
  let refreshing = false;
  let refreshMessage = '';

  // Seed the store immediately from SSR/load data — no waiting on fetch
  $: companies.set(data.companies ?? []);

  async function handleRefresh() {
    refreshing = true;
    refreshMessage = 'Refresh started — this may take ~2min…';
    try {
      await fetch(`${API}/refresh`, { method: 'POST' });
      setTimeout(async () => {
        const res = await fetch(`${API}/companies`);
        if (res.ok) companies.set(await res.json());
        refreshMessage = 'Data refreshed!';
        setTimeout(() => (refreshMessage = ''), 3000);
        refreshing = false;
      }, 35_000);
    } catch {
      refreshMessage = 'Refresh failed — check console.';
      refreshing = false;
    }
  }

  function selectCompany(id) {
    selectedId.set(id);
    const card = listEl?.querySelector(`[data-id="${id}"]`);
    card?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
</script>

<svelte:head>
  <title>TechMap India</title>
</svelte:head>

<div class="flex flex-col h-screen overflow-hidden bg-gray-50">
  <!-- ── Header ── -->
  <header class="flex items-center justify-between px-4 py-3 bg-gray-900 text-white shrink-0 z-10 shadow-md">
    <div class="flex items-center gap-3">
      <span class="text-xl font-bold tracking-tight">TechMap</span>
      <span class="text-gray-400 text-sm hidden sm:block">India IT Companies</span>
    </div>

    <div class="flex items-center gap-3">
      <CitySearch />

      {#if refreshMessage}
        <span class="text-xs text-yellow-300">{refreshMessage}</span>
      {/if}

      <button
        on:click={handleRefresh}
        disabled={refreshing}
        class="text-sm bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed
               px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap"
      >
        {refreshing ? 'Refreshing…' : 'Refresh Data'}
      </button>
    </div>
  </header>

  <!-- ── Body ── -->
  <div class="flex flex-1 overflow-hidden flex-col md:flex-row">

    <!-- ── Left Sidebar ── -->
    <aside class="w-full md:w-80 shrink-0 flex flex-col overflow-hidden border-r border-gray-200 bg-white
                  h-64 md:h-auto">
      <FilterBar />

      {#if $filtered.length === 0}
        <div class="flex-1 flex items-center justify-center text-gray-400 text-sm">
          No companies found for this filter.
        </div>

      {:else}
        <p class="text-xs text-gray-400 px-3 py-1 border-b">
          Showing {$filtered.length} {$filtered.length === 1 ? 'company' : 'companies'}
        </p>
        <ul bind:this={listEl} class="overflow-y-auto flex-1">
          {#each $filtered as c (c.id)}
            <li data-id={c.id}>
              <CompanyCard
                company={c}
                selected={$selectedId === c.id}
                on:click={() => selectCompany(c.id)}
              />
            </li>
          {/each}
        </ul>
      {/if}
    </aside>

    <!-- ── Map ── -->
    <main class="flex-1 min-h-0 flex flex-col">
      <Map on:select={(e) => selectCompany(e.detail)} />
    </main>
  </div>
</div>
