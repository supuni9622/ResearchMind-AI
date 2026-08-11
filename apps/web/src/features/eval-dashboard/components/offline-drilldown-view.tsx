'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type EvalScore, type OfflineExampleSummary } from '@/lib/api';
import { EmptyState } from '@/components/ui/empty-state';
import { OfflineExamplePicker } from '@/features/eval-dashboard/components/offline-example-picker';
import { ScoreTable } from '@/features/eval-dashboard/components/score-table';

const PAGE_SIZE = 20;
const SEARCH_DEBOUNCE_MS = 300;

export function OfflineDrilldownView({ onForbidden }: { onForbidden: () => void }) {
  const [exampleSearch, setExampleSearch] = useState('');
  const [debouncedExampleSearch, setDebouncedExampleSearch] = useState('');
  const [examples, setExamples] = useState<OfflineExampleSummary[]>([]);
  const [examplesLoading, setExamplesLoading] = useState(true);

  const [selectedExample, setSelectedExample] = useState<OfflineExampleSummary | null>(null);
  const [scores, setScores] = useState<EvalScore[]>([]);
  const [scoresTotal, setScoresTotal] = useState(0);
  const [scoresLoading, setScoresLoading] = useState(false);
  const [scoresPage, setScoresPage] = useState(1);

  const examplesRequestId = useRef(0);
  const scoresRequestId = useRef(0);

  useEffect(() => {
    const timer = setTimeout(
      () => setDebouncedExampleSearch(exampleSearch.trim()),
      SEARCH_DEBOUNCE_MS
    );
    return () => clearTimeout(timer);
  }, [exampleSearch]);

  const loadExamples = useCallback(
    async (search: string) => {
      const requestId = ++examplesRequestId.current;
      setExamplesLoading(true);
      try {
        const res = await api.evalDashboard.listOfflineExamples({
          search: search || undefined,
          limit: 30,
        });
        if (examplesRequestId.current !== requestId) return;
        setExamples(res.items);
      } catch (err) {
        if (examplesRequestId.current !== requestId) return;
        if (err instanceof Error && (err as Error & { status?: number }).status === 403) {
          onForbidden();
        }
      } finally {
        if (examplesRequestId.current === requestId) setExamplesLoading(false);
      }
    },
    [onForbidden]
  );

  useEffect(() => {
    loadExamples(debouncedExampleSearch);
  }, [debouncedExampleSearch, loadExamples]);

  const loadExampleScores = useCallback(
    async (example: OfflineExampleSummary, page: number) => {
      const requestId = ++scoresRequestId.current;
      setScoresLoading(true);
      try {
        const res = await api.evalDashboard.listOfflineScores({
          datasetExampleId: example.dataset_example_id,
          limit: PAGE_SIZE,
          offset: (page - 1) * PAGE_SIZE,
        });
        if (scoresRequestId.current !== requestId) return;
        setScores(res.items);
        setScoresTotal(res.total);
      } catch (err) {
        if (scoresRequestId.current !== requestId) return;
        if (err instanceof Error && (err as Error & { status?: number }).status === 403) {
          onForbidden();
        }
      } finally {
        if (scoresRequestId.current === requestId) setScoresLoading(false);
      }
    },
    [onForbidden]
  );

  useEffect(() => {
    if (!selectedExample) return;
    loadExampleScores(selectedExample, scoresPage);
  }, [selectedExample, scoresPage, loadExampleScores]);

  function handleSelectExample(example: OfflineExampleSummary) {
    setSelectedExample(example);
    setScoresPage(1);
  }

  const totalPages = Math.max(1, Math.ceil(scoresTotal / PAGE_SIZE));

  return (
    <div className="flex gap-6">
      <OfflineExamplePicker
        search={exampleSearch}
        onSearchChange={setExampleSearch}
        examples={examples}
        loading={examplesLoading}
        selectedExampleId={selectedExample?.dataset_example_id ?? null}
        onSelect={handleSelectExample}
      />

      <div className="flex-1 min-w-0">
        {!selectedExample ? (
          <EmptyState
            title="Select a golden-set example"
            description="Pick an example from the list to see its GoldenSetGeneration run history — each run is a new row, not an overwrite, so this is a trend, not a single score."
          />
        ) : (
          <>
            <div className="mb-6">
              <p className="font-display text-amber-400 text-[15px] mb-1 font-mono">
                {selectedExample.dataset_example_id}
              </p>
              <p className="text-stone-600 text-[12px]">
                {selectedExample.score_count} score{selectedExample.score_count === 1 ? '' : 's'}{' '}
                across every run so far — most recent first below.
              </p>
            </div>

            {scoresLoading ? (
              <div className="text-center py-16 border border-dashed border-ink-600 rounded-xl">
                <p className="text-stone-600 text-sm">Loading…</p>
              </div>
            ) : scores.length === 0 ? (
              <EmptyState title="No offline scores for this example yet" />
            ) : (
              <>
                <ScoreTable scores={scores} />

                {totalPages > 1 && (
                  <div className="flex items-center justify-between pt-4">
                    <span className="font-mono text-stone-600 text-[11px]">
                      Page {scoresPage} of {totalPages}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setScoresPage((p) => Math.max(1, p - 1))}
                        disabled={scoresPage === 1}
                        className="px-3 py-1.5 rounded-lg border border-ink-600 text-stone-300 text-[13px] hover:border-ink-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        Previous
                      </button>
                      <button
                        type="button"
                        onClick={() => setScoresPage((p) => Math.min(totalPages, p + 1))}
                        disabled={scoresPage === totalPages}
                        className="px-3 py-1.5 rounded-lg border border-ink-600 text-stone-300 text-[13px] hover:border-ink-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
