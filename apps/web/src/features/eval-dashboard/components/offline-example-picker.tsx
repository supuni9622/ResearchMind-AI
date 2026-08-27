import type { OfflineExampleSummary } from '@/lib/api';

export function OfflineExamplePicker({
  search,
  onSearchChange,
  examples,
  loading,
  selectedExampleId,
  onSelect,
  page,
  totalPages,
  onPageChange,
}: {
  search: string;
  onSearchChange: (value: string) => void;
  examples: OfflineExampleSummary[];
  loading: boolean;
  selectedExampleId: string | null;
  onSelect: (example: OfflineExampleSummary) => void;
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  return (
    <div className="w-72 flex-shrink-0 border-r border-ink-700 pr-5">
      <input
        type="text"
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search dataset_example_id…"
        className="w-full px-3 py-2 rounded-lg bg-ink-800 border border-ink-600 text-stone-200 text-[13px] placeholder:text-stone-600 focus:outline-none focus:border-sage-600 mb-3"
      />

      {loading ? (
        <p className="text-stone-600 text-[12px] px-1">Loading…</p>
      ) : examples.length === 0 ? (
        <p className="text-stone-600 text-[12px] px-1">
          {search
            ? 'No matching examples.'
            : 'No offline benchmark runs persisted yet — run persist_golden_set_scores.py after a GoldenSetGeneration run.'}
        </p>
      ) : (
        <>
          <div className="space-y-1">
            {examples.map((example) => (
              <button
                key={example.dataset_example_id}
                onClick={() => onSelect(example)}
                className={`w-full text-left px-3 py-2 rounded-lg border transition-colors duration-100 ${
                  selectedExampleId === example.dataset_example_id
                    ? 'border-sage-600 bg-sage-800/20'
                    : 'border-transparent hover:border-ink-500 hover:bg-ink-800/40'
                }`}
              >
                <p className="font-mono text-stone-200 text-[13px] truncate">
                  {example.dataset_example_id}
                </p>
                <p className="font-mono text-stone-600 text-[10px]">
                  {example.score_count} score{example.score_count === 1 ? '' : 's'}
                </p>
              </button>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-3 mt-2 border-t border-ink-700">
              <span className="font-mono text-stone-600 text-[11px]">
                {page}/{totalPages}
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => onPageChange(Math.max(1, page - 1))}
                  disabled={page === 1}
                  className="px-2.5 py-1 rounded-lg border border-ink-600 text-stone-300 text-[12px] hover:border-ink-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Prev
                </button>
                <button
                  type="button"
                  onClick={() => onPageChange(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  className="px-2.5 py-1 rounded-lg border border-ink-600 text-stone-300 text-[12px] hover:border-ink-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
