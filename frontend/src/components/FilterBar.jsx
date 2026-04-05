import { useApp } from '../store/AppContext.jsx';

const FILTERS = [
  { key: null,        label: 'All' },
  { key: 'software',  label: 'Software / Dev' },
  { key: 'itsupport', label: 'IT Support' },
  { key: 'cloud',     label: 'Cloud / SaaS' },
  { key: 'unknown',   label: 'Unknown' },
];

const ACTIVE_CLASSES = {
  null:       'bg-gray-800 text-white',
  software:   'bg-blue-600 text-white',
  itsupport:  'bg-green-600 text-white',
  cloud:      'bg-purple-600 text-white',
  unknown:    'bg-gray-500 text-white',
};

const INACTIVE_CLASSES = {
  null:       'bg-gray-100 text-gray-700 hover:bg-gray-200',
  software:   'bg-blue-50 text-blue-700 hover:bg-blue-100',
  itsupport:  'bg-green-50 text-green-700 hover:bg-green-100',
  cloud:      'bg-purple-50 text-purple-700 hover:bg-purple-100',
  unknown:    'bg-gray-100 text-gray-600 hover:bg-gray-200',
};

export default function FilterBar() {
  const { activeFilter, setActiveFilter, companies, countByType } = useApp();

  function count(key) {
    if (key === null) return companies.length;
    return countByType[key] ?? 0;
  }

  return (
    <div className="flex flex-wrap gap-2 p-3 border-b bg-white">
      {FILTERS.map(f => {
        const isActive = activeFilter === f.key;
        const cls = isActive ? ACTIVE_CLASSES[f.key] : INACTIVE_CLASSES[f.key];
        return (
          <button
            key={f.key ?? 'all'}
            className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-full transition-colors ${cls}`}
            onClick={() => setActiveFilter(f.key)}
          >
            {f.label}
            <span className="font-bold">{count(f.key)}</span>
          </button>
        );
      })}
    </div>
  );
}
