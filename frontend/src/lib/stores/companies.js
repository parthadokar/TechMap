import { writable, derived } from 'svelte/store';

/** @type {import('svelte/store').Writable<Array>} */
export const companies = writable([]);

/** Currently highlighted company id (set by card click or map pin click) */
export const selectedId = writable(null);

/** City search result bounds — map zooms to this when set */
export const cityBounds = writable(null); // { south, north, west, east }

/** Active subtype filter — null means show all */
export const activeFilter = writable(null);

/** Loading / error state */
export const loading = writable(false);
export const error   = writable(null);

/**
 * Filtered company list — drives both the sidebar list and the map markers.
 */
export const filtered = derived(
  [companies, activeFilter],
  ([$companies, $filter]) => {
    if (!$filter) return $companies;
    return $companies.filter(c => c.type === $filter);
  }
);

/**
 * Count by subtype — used by the filter bar badges.
 */
export const countByType = derived(companies, ($companies) => {
  const counts = { software: 0, itsupport: 0, cloud: 0, unknown: 0 };
  for (const c of $companies) {
    const key = c.type ?? 'unknown';
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts;
});
