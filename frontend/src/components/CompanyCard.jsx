const TYPE_META = {
  software:  { label: 'Software / Dev',   bg: 'bg-blue-100 dark:bg-blue-900/40',   text: 'text-blue-700 dark:text-blue-300'   },
  itsupport: { label: 'IT Support / MSP', bg: 'bg-green-100 dark:bg-green-900/40',  text: 'text-green-700 dark:text-green-300'  },
  cloud:     { label: 'Cloud / SaaS',     bg: 'bg-purple-100 dark:bg-purple-900/40', text: 'text-purple-700 dark:text-purple-300' },
  unknown:   { label: 'Unknown',          bg: 'bg-gray-100 dark:bg-gray-700',   text: 'text-gray-600 dark:text-gray-300'   },
};

export default function CompanyCard({ company, selected, onClick }) {
  const meta = TYPE_META[company.type] ?? TYPE_META.unknown;

  return (
    <div
      className={`p-3 border-b dark:border-gray-700 cursor-pointer transition-colors duration-150 ${
        selected
          ? 'bg-blue-50 dark:bg-blue-900/30 border-l-4 border-l-blue-500'
          : 'hover:bg-gray-50 dark:hover:bg-gray-800 border-l-4 border-l-transparent'
      }`}
      onClick={onClick}
      onKeyDown={e => e.key === 'Enter' && onClick?.()}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 leading-tight">{company.name}</p>
        <span className={`shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded-full ${meta.bg} ${meta.text}`}>
          {meta.label}
        </span>
      </div>

      {company.address && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">{company.address}</p>
      )}

      <div className="flex items-center gap-3 mt-1.5 flex-wrap">
        {company.phone && (
          <a
            href={`tel:${company.phone}`}
            className="text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
            onClick={e => e.stopPropagation()}
          >
            {company.phone}
          </a>
        )}
        {company.website && (
          <a
            href={company.website}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-600 dark:text-blue-400 hover:underline truncate max-w-[160px]"
            onClick={e => e.stopPropagation()}
          >
            {company.website.replace(/^https?:\/\//, '')}
          </a>
        )}
      </div>
    </div>
  );
}
