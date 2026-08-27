import type { OwnerSummary } from '@/lib/api';

export function OwnerPicker({
  search,
  onSearchChange,
  owners,
  loading,
  selectedOwnerId,
  onSelect,
}: {
  search: string;
  onSearchChange: (value: string) => void;
  owners: OwnerSummary[];
  loading: boolean;
  selectedOwnerId: string | null;
  onSelect: (owner: OwnerSummary) => void;
}) {
  return (
    <div className="w-72 flex-shrink-0 border-r border-ink-700 pr-5">
      <input
        type="text"
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search by email or username…"
        className="w-full px-3 py-2 rounded-lg bg-ink-800 border border-ink-600 text-stone-200 text-[13px] placeholder:text-stone-600 focus:outline-none focus:border-sage-600 mb-3"
      />

      {loading ? (
        <p className="text-stone-600 text-[12px] px-1">Loading…</p>
      ) : owners.length === 0 ? (
        <p className="text-stone-600 text-[12px] px-1">
          {search ? 'No matching owners.' : 'No owners have eval data yet.'}
        </p>
      ) : (
        <div className="space-y-1">
          {owners.map((owner) => (
            <button
              key={owner.owner_id}
              onClick={() => onSelect(owner)}
              className={`w-full text-left px-3 py-2 rounded-lg border transition-colors duration-100 ${
                selectedOwnerId === owner.owner_id
                  ? 'border-sage-600 bg-sage-800/20'
                  : 'border-transparent hover:border-ink-500 hover:bg-ink-800/40'
              }`}
            >
              <p className="text-stone-200 text-[13px] truncate">
                {owner.username || owner.email}
              </p>
              <p className="font-mono text-stone-600 text-[10px]">
                {owner.score_count} score{owner.score_count === 1 ? '' : 's'}
              </p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
