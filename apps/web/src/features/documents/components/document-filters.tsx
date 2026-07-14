import { Pill } from '@/components/ui/badge';
import { SearchIcon } from '@/components/ui/icons';
import type { DocKind } from '@/features/documents/mock-meta';

const FILTERS: { id: DocKind | 'all'; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'pdf', label: 'PDF' },
  { id: 'docx', label: 'DOCX' },
  { id: 'markdown', label: 'Markdown' },
];

export function DocumentFilters({
  active,
  onChange,
  search,
  onSearchChange,
}: {
  active: DocKind | 'all';
  onChange: (kind: DocKind | 'all') => void;
  search: string;
  onSearchChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-5">
      <div className="flex items-center gap-1.5 flex-wrap">
        {FILTERS.map((f) => (
          <Pill key={f.id} active={active === f.id} onClick={() => onChange(f.id)}>
            {f.label}
          </Pill>
        ))}
      </div>
      <div className="relative sm:ml-auto sm:w-64">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-600">
          <SearchIcon size={13} />
        </span>
        <input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search documents…"
          className="w-full bg-ink-800 border border-ink-600 rounded-lg pl-8 pr-3 py-1.5 text-stone-200 text-[13px] placeholder-stone-600 focus:outline-none focus:border-sage-600 transition-colors"
        />
      </div>
    </div>
  );
}
