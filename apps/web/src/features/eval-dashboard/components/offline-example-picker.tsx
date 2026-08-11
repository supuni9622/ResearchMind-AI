import type { OfflineExampleSummary } from '@/lib/api';

export function OfflineExamplePicker({
  search,
  onSearchChange,
  examples,
  loading,
  selectedExampleId,
  onSelect,
}: {
  search: string;
  onSearchChange: (value: string) => void;
  examples: OfflineExampleSummary[];
  loading: boolean;
  selectedExampleId: string | null;
  onSelect: (example: OfflineExampleSummary) => void;
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
      )}
    </div>
  );
}
