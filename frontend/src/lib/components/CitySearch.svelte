<script>
  import { companies, cityBounds } from '$lib/stores/companies';

  const API = 'http://localhost:8000';

  let query = '';
  let loading = false;
  let error = '';
  let resultLabel = '';

  async function search() {
    const city = query.trim();
    if (!city) return;

    loading = true;
    error = '';
    resultLabel = '';

    try {
      const res = await fetch(`${API}/search?city=${encodeURIComponent(city)}`);
      if (res.status === 404) {
        error = `"${city}" not found in India`;
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();

      // Merge new companies into the store (avoid duplicates by id)
      companies.update(existing => {
        const existingIds = new Set(existing.map(c => c.id));
        const newOnes = data.companies.filter(c => !existingIds.has(c.id));
        return [...existing, ...newOnes];
      });

      // Signal the map to zoom to this city
      cityBounds.set(data.bounds);

      resultLabel = `${data.companies.length} companies in ${data.display_name.split(',')[0]}`;
    } catch (e) {
      error = 'Search failed — is the backend running?';
    } finally {
      loading = false;
    }
  }

  function onKeydown(e) {
    if (e.key === 'Enter') search();
  }
</script>

<div class="flex flex-col gap-1">
  <div class="flex gap-2">
    <input
      bind:value={query}
      on:keydown={onKeydown}
      placeholder="Search city (e.g. Bangalore)"
      disabled={loading}
      class="flex-1 text-sm bg-gray-800 text-white placeholder-gray-400 border border-gray-600
             rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-400 disabled:opacity-50"
    />
    <button
      on:click={search}
      disabled={loading || !query.trim()}
      class="text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed
             px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap"
    >
      {loading ? '…' : 'Search'}
    </button>
  </div>

  {#if error}
    <p class="text-red-400 text-xs px-1">{error}</p>
  {:else if resultLabel}
    <p class="text-green-400 text-xs px-1">{resultLabel}</p>
  {/if}
</div>
