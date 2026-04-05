import { useEffect, useRef, useState } from 'react';
import { AppProvider, useApp } from './store/AppContext.jsx';
import FilterBar from './components/FilterBar.jsx';
import CompanyCard from './components/CompanyCard.jsx';
import Map from './components/Map.jsx';
import CitySearch from './components/CitySearch.jsx';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

function AppContent() {
  const { companies, setCompanies, filtered, selectedId, setSelectedId } = useApp();
  const listRef = useRef(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState('');

  useEffect(() => {
    fetch(`${API}/companies`)
      .then(res => (res.ok ? res.json() : []))
      .then(data => setCompanies(data))
      .catch(() => {});
  }, []);

  // If companies are still empty (DB seeding in background), poll every 5s until data arrives
  useEffect(() => {
    if (companies.length > 0) return;
    const interval = setInterval(() => {
      fetch(`${API}/companies`)
        .then(res => (res.ok ? res.json() : []))
        .then(data => { if (data.length > 0) setCompanies(data); })
        .catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [companies.length]);

  async function handleRefresh() {
    setRefreshing(true);
    setRefreshMessage('Refresh started — this may take ~2min…');
    try {
      await fetch(`${API}/refresh`, { method: 'POST' });
      setTimeout(async () => {
        const res = await fetch(`${API}/companies`);
        if (res.ok) setCompanies(await res.json());
        setRefreshMessage('Data refreshed!');
        setTimeout(() => setRefreshMessage(''), 3000);
        setRefreshing(false);
      }, 35_000);
    } catch {
      setRefreshMessage('Refresh failed — check console.');
      setRefreshing(false);
    }
  }

  function selectCompany(id) {
    setSelectedId(id);
    const card = listRef.current?.querySelector(`[data-id="${id}"]`);
    card?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 bg-gray-900 text-white shrink-0 z-10 shadow-md">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold tracking-tight">TechMap</span>
          <span className="text-gray-400 text-sm hidden sm:block">India IT Companies</span>
        </div>
        <div className="flex items-center gap-3">
          <CitySearch />
          {refreshMessage && (
            <span className="text-xs text-yellow-300">{refreshMessage}</span>
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="text-sm bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap"
          >
            {refreshing ? 'Refreshing…' : 'Refresh Data'}
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden flex-col md:flex-row">
        {/* Sidebar */}
        <aside className="w-full md:w-80 shrink-0 flex flex-col overflow-hidden border-r border-gray-200 bg-white h-64 md:h-auto">
          <FilterBar />
          {filtered.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-2 text-gray-400 text-sm px-4 text-center">
              {companies.length === 0 ? (
                <>
                  <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
                  <span>Loading companies…</span>
                  <span className="text-xs text-gray-300">First run fetches from OpenStreetMap (~1 min)</span>
                </>
              ) : (
                <span>No companies found for this filter.</span>
              )}
            </div>
          ) : (
            <>
              <p className="text-xs text-gray-400 px-3 py-1 border-b">
                Showing {filtered.length} {filtered.length === 1 ? 'company' : 'companies'}
              </p>
              <ul ref={listRef} className="overflow-y-auto flex-1">
                {filtered.map(c => (
                  <li key={c.id} data-id={c.id}>
                    <CompanyCard
                      company={c}
                      selected={selectedId === c.id}
                      onClick={() => selectCompany(c.id)}
                    />
                  </li>
                ))}
              </ul>
            </>
          )}
        </aside>

        {/* Map */}
        <main className="flex-1 min-h-0 flex flex-col">
          <Map onSelect={selectCompany} />
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
