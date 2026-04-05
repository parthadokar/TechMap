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
  const [dark, setDark] = useState(() => localStorage.getItem('theme') !== 'light');

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  }, [dark]);

  useEffect(() => {
    fetch(`${API}/companies`)
      .then(res => (res.ok ? res.json() : []))
      .then(data => setCompanies(data))
      .catch(() => {});
  }, []);

  async function deleteAllCompanies() {
    if (!window.confirm(`Delete all ${companies.length} companies from the database? This cannot be undone.`)) return;
    try {
      const res = await fetch(`${API}/companies`, { method: 'DELETE' });
      if (res.ok) {
        const { deleted } = await res.json();
        setCompanies([]);
        setRefreshMessage(`Deleted ${deleted} companies.`);
        setTimeout(() => setRefreshMessage(''), 3000);
      }
    } catch {
      setRefreshMessage('Delete failed — check console.');
    }
  }

  async function startRefresh(endpoint, label) {
    setRefreshing(true);
    setRefreshMessage(`${label}…`);
    try {
      await fetch(`${API}${endpoint}`, { method: 'POST' });
      // Poll /status until the backend finishes instead of a fixed timeout
      const poll = setInterval(async () => {
        try {
          const st = await fetch(`${API}/status`).then(r => r.json());
          if (!st.seeding) {
            clearInterval(poll);
            const data = await fetch(`${API}/companies`).then(r => r.json());
            setCompanies(data);
            setRefreshMessage('Done!');
            setTimeout(() => setRefreshMessage(''), 3000);
            setRefreshing(false);
          }
        } catch { /* backend busy */ }
      }, 3000);
    } catch {
      setRefreshMessage('Refresh failed — check console.');
      setRefreshing(false);
    }
  }

  const [seedingCount, setSeedingCount] = useState(0);

  // Poll /status while seeding; switch to /companies once data arrives
  useEffect(() => {
    if (companies.length > 0) return;
    const interval = setInterval(async () => {
      try {
        const st = await fetch(`${API}/status`).then(r => r.json());
        setSeedingCount(st.count ?? 0);
        if (!st.seeding && st.count > 0) {
          const data = await fetch(`${API}/companies`).then(r => r.json());
          if (data.length > 0) setCompanies(data);
        }
      } catch { /* backend not ready yet */ }
    }, 4000);
    return () => clearInterval(interval);
  }, [companies.length]);

  function selectCompany(id) {
    setSelectedId(id);
    const card = listRef.current?.querySelector(`[data-id="${id}"]`);
    card?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 bg-gray-900 text-white shrink-0 z-10 shadow-md">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold tracking-tight">TechMap</span>
          <span className="text-gray-400 text-sm hidden sm:block">India IT Companies</span>
        </div>
        <div className="flex items-center gap-3">
          <CitySearch />
          {/* Dark mode toggle */}
          <button
            onClick={() => setDark(d => !d)}
            title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
            className="text-gray-300 hover:text-white p-1.5 rounded-lg hover:bg-gray-700 transition-colors"
          >
            {dark ? (
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m8.66-9h-1M4.34 12h-1m15.07-6.07-.71.71M6.34 17.66l-.71.71m12.02 0-.71-.71M6.34 6.34l-.71-.71M12 5a7 7 0 100 14A7 7 0 0012 5z" /></svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" /></svg>
            )}
          </button>
          {refreshMessage && (
            <span className="text-xs text-yellow-300 whitespace-nowrap">{refreshMessage}</span>
          )}

          {/* Metro — top 10 metros only (~10–15s), fastest */}
          <button
            onClick={() => startRefresh('/refresh/metro', 'Refreshing metros')}
            disabled={refreshing}
            title="Mumbai, Delhi, Bengaluru, Hyderabad, Chennai, Pune, Kolkata, Ahmedabad, Noida, Gurgaon (~10–15s)"
            className="text-sm bg-green-600 hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap"
          >
            {refreshing ? 'Refreshing…' : 'Metro Cities'}
          </button>

          {/* All IT cities (~30–45s) */}
          <button
            onClick={() => startRefresh('/refresh/cities', 'Refreshing cities')}
            disabled={refreshing}
            title="All 35 major IT cities across India (~30–45s)"
            className="text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap"
          >
            All Cities
          </button>

          {/* Full India (~1–2 min) */}
          <button
            onClick={() => startRefresh('/refresh', 'Full refresh')}
            disabled={refreshing}
            title="Full sweep of all companies across India (~1–2 minutes)"
            className="text-sm bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap"
          >
            Full Refresh
          </button>

          {/* GitHub orgs */}
          <button
            onClick={() => startRefresh('/refresh/github', 'Fetching GitHub orgs')}
            disabled={refreshing}
            title="Find Indian tech organisations on GitHub and add them to the map"
            className="text-sm bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap"
          >
            + GitHub
          </button>

          {/* Delete all */}
          <button
            onClick={deleteAllCompanies}
            disabled={refreshing || companies.length === 0}
            title="Delete all companies from the database"
            className="text-sm bg-red-600 hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap"
          >
            Clear All
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden flex-col md:flex-row">
        {/* Sidebar */}
        <aside className="w-full md:w-80 shrink-0 flex flex-col overflow-hidden border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 h-64 md:h-auto">
          <FilterBar />
          {filtered.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-2 text-gray-400 dark:text-gray-500 text-sm px-4 text-center">
              {companies.length === 0 ? (
                <>
                  <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
                  <span>Fetching companies…</span>
                  {seedingCount > 0 && (
                    <span className="text-xs text-blue-400 font-medium">{seedingCount} found so far</span>
                  )}
                  <span className="text-xs text-gray-300">First run pulls from OpenStreetMap (~1 min)</span>
                </>
              ) : (
                <span>No companies found for this filter.</span>
              )}
            </div>
          ) : (
            <>
              <p className="text-xs text-gray-400 dark:text-gray-500 px-3 py-1 border-b dark:border-gray-700">
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
