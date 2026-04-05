import { useState } from 'react';
import { useApp } from '../store/AppContext.jsx';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export default function CitySearch() {
  const { setCompanies, setCityBounds } = useApp();
  const [query, setQuery]           = useState('');
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [resultLabel, setResultLabel] = useState('');
  const [failedQuery, setFailedQuery] = useState(''); // the exact query that errored

  function handleChange(e) {
    setQuery(e.target.value);
    setError('');          // clear error as soon as user edits
    setFailedQuery('');    // re-enable the button
  }

  async function search() {
    const city = query.trim();
    if (!city) return;

    setLoading(true);
    setError('');
    setResultLabel('');

    try {
      const res = await fetch(`${API}/search?city=${encodeURIComponent(city)}`);

      if (res.status === 404) {
        setError(`"${city}" not found in India. Check the spelling or try a nearby city.`);
        setFailedQuery(city);   // lock the button for this exact query
        return;
      }

      if (!res.ok) {
        setError(`Server error (${res.status}) — try again in a moment.`);
        setFailedQuery(city);
        return;
      }

      const data = await res.json();

      setCompanies(existing => {
        const existingIds = new Set(existing.map(c => c.id));
        const newOnes = data.companies.filter(c => !existingIds.has(c.id));
        return [...existing, ...newOnes];
      });

      setCityBounds(data.bounds);
      setResultLabel(`${data.companies.length} companies in ${data.display_name.split(',')[0]}`);
    } catch {
      setError('Could not reach the backend — is it running?');
      setFailedQuery(city);
    } finally {
      setLoading(false);
    }
  }

  // Disable when: loading, empty input, or same query that already failed
  const isDisabled = loading || !query.trim() || query.trim() === failedQuery;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex gap-2">
        <input
          value={query}
          onChange={handleChange}
          onKeyDown={e => e.key === 'Enter' && !isDisabled && search()}
          placeholder="Search city (e.g. Bangalore)"
          disabled={loading}
          className="flex-1 text-sm bg-gray-800 text-white placeholder-gray-400 border border-gray-600 rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-400 disabled:opacity-50"
        />
        <button
          onClick={search}
          disabled={isDisabled}
          className="text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap"
        >
          {loading ? '…' : 'Search'}
        </button>
      </div>
      {error       && <p className="text-red-400 text-xs px-1">{error}</p>}
      {!error && resultLabel && <p className="text-green-400 text-xs px-1">{resultLabel}</p>}
    </div>
  );
}
