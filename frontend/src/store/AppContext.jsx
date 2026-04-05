import { createContext, useContext, useState, useMemo } from 'react';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [companies, setCompanies] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [cityBounds, setCityBounds] = useState(null);
  const [activeFilter, setActiveFilter] = useState(null);

  const filtered = useMemo(() => {
    if (!activeFilter) return companies;
    return companies.filter(c => c.type === activeFilter);
  }, [companies, activeFilter]);

  const countByType = useMemo(() => {
    const counts = { software: 0, itsupport: 0, cloud: 0, unknown: 0 };
    for (const c of companies) {
      const key = c.type ?? 'unknown';
      counts[key] = (counts[key] ?? 0) + 1;
    }
    return counts;
  }, [companies]);

  return (
    <AppContext.Provider value={{
      companies, setCompanies,
      selectedId, setSelectedId,
      cityBounds, setCityBounds,
      activeFilter, setActiveFilter,
      filtered,
      countByType,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  return useContext(AppContext);
}
