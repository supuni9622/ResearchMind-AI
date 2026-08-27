'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type EvalScore, type OwnerSummary } from '@/lib/api';
import { EmptyState } from '@/components/ui/empty-state';
import { Pill } from '@/components/ui/badge';
import { OwnerPicker } from '@/features/eval-dashboard/components/owner-picker';
import { ScoreTable } from '@/features/eval-dashboard/components/score-table';
import { ReviewDecisionSummary } from '@/features/eval-dashboard/components/review-decision-summary';

const PAGE_SIZE = 20;
const SEARCH_DEBOUNCE_MS = 300;

// No "Offline" entry here -- offline-benchmark rows have no owner_id,
// so filtering this owner-scoped view by that source always returns
// zero rows. See OfflineDrilldownView for that data instead.
const SOURCE_FILTERS: { value: string | null; label: string }[] = [
  { value: null, label: 'All' },
  { value: 'online_sampled', label: 'Online' },
  { value: 'human_feedback', label: 'Feedback' },
];

export function OwnerDrilldownView({ onForbidden }: { onForbidden: () => void }) {
  const [ownerSearch, setOwnerSearch] = useState('');
  const [debouncedOwnerSearch, setDebouncedOwnerSearch] = useState('');
  const [owners, setOwners] = useState<OwnerSummary[]>([]);
  const [ownersLoading, setOwnersLoading] = useState(true);

  const [selectedOwner, setSelectedOwner] = useState<OwnerSummary | null>(null);
  const [scores, setScores] = useState<EvalScore[]>([]);
  const [scoresTotal, setScoresTotal] = useState(0);
  const [scoresLoading, setScoresLoading] = useState(false);
  const [scoresPage, setScoresPage] = useState(1);
  const [sourceFilter, setSourceFilter] = useState<string | null>(null);

  const [reviewCounts, setReviewCounts] = useState<Record<string, number>>({});

  const ownersRequestId = useRef(0);
  const scoresRequestId = useRef(0);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedOwnerSearch(ownerSearch.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [ownerSearch]);

  const loadOwners = useCallback(
    async (search: string) => {
      const requestId = ++ownersRequestId.current;
      setOwnersLoading(true);
      try {
        const res = await api.evalDashboard.listOwners({ search: search || undefined, limit: 30 });
        if (ownersRequestId.current !== requestId) return;
        setOwners(res.items);
      } catch (err) {
        if (ownersRequestId.current !== requestId) return;
        if (err instanceof Error && (err as Error & { status?: number }).status === 403) {
          onForbidden();
        }
      } finally {
        if (ownersRequestId.current === requestId) setOwnersLoading(false);
      }
    },
    [onForbidden]
  );

  useEffect(() => {
    loadOwners(debouncedOwnerSearch);
  }, [debouncedOwnerSearch, loadOwners]);

  const loadOwnerDetail = useCallback(
    async (owner: OwnerSummary, page: number, source: string | null) => {
      const requestId = ++scoresRequestId.current;
      setScoresLoading(true);
      try {
        const [scoresRes, reviewRes] = await Promise.all([
          api.evalDashboard.listScores(owner.owner_id, {
            source: source ?? undefined,
            limit: PAGE_SIZE,
            offset: (page - 1) * PAGE_SIZE,
          }),
          api.evalDashboard.reviewDecisions(owner.owner_id),
        ]);
        if (scoresRequestId.current !== requestId) return;
        setScores(scoresRes.items);
        setScoresTotal(scoresRes.total);
        setReviewCounts(reviewRes.counts);
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
    if (!selectedOwner) return;
    loadOwnerDetail(selectedOwner, scoresPage, sourceFilter);
  }, [selectedOwner, scoresPage, sourceFilter, loadOwnerDetail]);

  function handleSelectOwner(owner: OwnerSummary) {
    setSelectedOwner(owner);
    setScoresPage(1);
    setSourceFilter(null);
  }

  const totalPages = Math.max(1, Math.ceil(scoresTotal / PAGE_SIZE));

  return (
    <div className="flex gap-6">
      <OwnerPicker
        search={ownerSearch}
        onSearchChange={setOwnerSearch}
        owners={owners}
        loading={ownersLoading}
        selectedOwnerId={selectedOwner?.owner_id ?? null}
        onSelect={handleSelectOwner}
      />

      <div className="flex-1 min-w-0">
        {!selectedOwner ? (
          <EmptyState
            title="Select an owner"
            description="Pick a user from the list to see their eval trend."
          />
        ) : (
          <>
            <div className="mb-6">
              <p className="font-display text-amber-400 text-[15px] mb-2">
                {selectedOwner.username || selectedOwner.email}
              </p>
              <ReviewDecisionSummary counts={reviewCounts} />
            </div>

            <div className="flex items-center gap-2 mb-4">
              {SOURCE_FILTERS.map((filter) => (
                <Pill
                  key={filter.label}
                  active={sourceFilter === filter.value}
                  onClick={() => {
                    setSourceFilter(filter.value);
                    setScoresPage(1);
                  }}
                >
                  {filter.label}
                </Pill>
              ))}
            </div>

            {scoresLoading ? (
              <div className="text-center py-16 border border-dashed border-ink-600 rounded-xl">
                <p className="text-stone-600 text-sm">Loading…</p>
              </div>
            ) : scores.length === 0 ? (
              <EmptyState
                title="No scores for this owner yet"
                description="Either nothing has run against their generations, or the current filter excludes everything."
              />
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
