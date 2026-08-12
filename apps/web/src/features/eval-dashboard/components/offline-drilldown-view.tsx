'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type BenchmarkReportResult, type EvalScore, type OfflineExampleSummary } from '@/lib/api';
import { EmptyState } from '@/components/ui/empty-state';
import { BenchmarkReportCard } from '@/features/eval-dashboard/components/benchmark-reports-view';
import { OfflineExamplePicker } from '@/features/eval-dashboard/components/offline-example-picker';
import { ScoreTable } from '@/features/eval-dashboard/components/score-table';

const PAGE_SIZE = 20;
const EXAMPLES_PAGE_SIZE = 30;
const SEARCH_DEBOUNCE_MS = 300;

export function OfflineDrilldownView({ onForbidden }: { onForbidden: () => void }) {
  const [summaries, setSummaries] = useState<BenchmarkReportResult[]>([]);
  const [summariesLoading, setSummariesLoading] = useState(true);

  const [exampleSearch, setExampleSearch] = useState('');
  const [debouncedExampleSearch, setDebouncedExampleSearch] = useState('');
  const [examples, setExamples] = useState<OfflineExampleSummary[]>([]);
  const [examplesTotal, setExamplesTotal] = useState(0);
  const [examplesPage, setExamplesPage] = useState(1);
  const [examplesLoading, setExamplesLoading] = useState(true);

  const [selectedExample, setSelectedExample] = useState<OfflineExampleSummary | null>(null);
  const [scores, setScores] = useState<EvalScore[]>([]);
  const [scoresTotal, setScoresTotal] = useState(0);
  const [scoresLoading, setScoresLoading] = useState(false);
  const [scoresPage, setScoresPage] = useState(1);

  const examplesRequestId = useRef(0);
  const scoresRequestId = useRef(0);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const res = await api.evalDashboard.offlineSummary();
        if (!cancelled) setSummaries(res);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof Error && (err as Error & { status?: number }).status === 403) {
          onForbidden();
        }
      } finally {
        if (!cancelled) setSummariesLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [onForbidden]);

  useEffect(() => {
    const timer = setTimeout(
      () => setDebouncedExampleSearch(exampleSearch.trim()),
      SEARCH_DEBOUNCE_MS
    );
    return () => clearTimeout(timer);
  }, [exampleSearch]);

  // A new search term always restarts at page 1 -- otherwise a stale
  // offset from a previous, longer result set could page past the end
  // of a narrower one.
  useEffect(() => {
    setExamplesPage(1);
  }, [debouncedExampleSearch]);

  const loadExamples = useCallback(
    async (search: string, page: number) => {
      const requestId = ++examplesRequestId.current;
      setExamplesLoading(true);
      try {
        const res = await api.evalDashboard.listOfflineExamples({
          search: search || undefined,
          limit: EXAMPLES_PAGE_SIZE,
          offset: (page - 1) * EXAMPLES_PAGE_SIZE,
        });
        if (examplesRequestId.current !== requestId) return;
        setExamples(res.items);
        setExamplesTotal(res.total);
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
    loadExamples(debouncedExampleSearch, examplesPage);
  }, [debouncedExampleSearch, examplesPage, loadExamples]);

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
  const examplesTotalPages = Math.max(1, Math.ceil(examplesTotal / EXAMPLES_PAGE_SIZE));

  return (
    <div>
      {!summariesLoading && summaries.length > 0 && (
        <div className="mb-6">
          <p className="text-stone-600 text-[12px] mb-3">
            Aggregate metrics from the latest local run of each — per-example detail is the
            picker below.
          </p>
          {summaries.map((report) => (
            <BenchmarkReportCard key={report.benchmark_name} report={report} />
          ))}
        </div>
      )}

      <div className="flex gap-6">
        <OfflineExamplePicker
          search={exampleSearch}
          onSearchChange={setExampleSearch}
          examples={examples}
          loading={examplesLoading}
          selectedExampleId={selectedExample?.dataset_example_id ?? null}
          onSelect={handleSelectExample}
          page={examplesPage}
          totalPages={examplesTotalPages}
          onPageChange={setExamplesPage}
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
                  {selectedExample.score_count} score
                  {selectedExample.score_count === 1 ? '' : 's'} across every run so far — most
                  recent first below.
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
    </div>
  );
}
