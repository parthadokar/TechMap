import { useState } from 'react';
import { useApp } from '../store/AppContext.jsx';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export default function CitySearch() {
  const { setCompanies, setCityBounds } = useApp();
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [resultLabel, setResultLabel] = useState('');

  async function search() {
    const city = query.trim();
    if (!city) return;

    setLoading(true);
    setError('');
    setResultLabel('');

    try {
      const res = await fetch(`${API}/search?city=${encodeURIComponent(city)}`);
      if (res.status === 404) {
        setError(`"${city}" not found in India`);
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();

      setCompanies(existing => {
        const existingIds = new Set(existing.map(c => c.id));
        const newOnes = data.companies.filter(c => !existingIds.has(c.id));
        return [...existing, ...newOnes];
      });

      setCityBounds(data.bounds);
      setResultLabel(`${data.companies.length} companies in ${data.display_name.split(',')[0]}`);
    } catch {
      setError('Search failed — is the backend running?');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex gap-2">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
          placeholder="Search city (e.g. Bangalore)"
          disabled={loading}
          className="flex-1 text-sm bg-gray-800 text-white placeholder-gray-400 border border-gray-600 rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-400 disabled:opacity-50"
        />
        <button
          onClick={search}
          disabled={loading || !query.trim()}
          className="text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap"
        >
          {loading ? '…' : 'Search'}
        </button>
      </div>
      {error && <p className="text-red-400 text-xs px-1">{error}</p>}
      {!error && resultLabel && <p className="text-green-400 text-xs px-1">{resultLabel}</p>}
    </div>
  );
}
