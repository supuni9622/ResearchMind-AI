'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { EmptyState } from '@/components/ui/empty-state';
import { PageHeader, SectionLabel } from '@/components/ui/page-header';
import { RefreshIcon } from '@/components/ui/icons';
import { SearchIcon } from '@/components/ui/icons';
import { Pill } from '@/components/ui/badge';
import { api, type MemoryRecord } from '@/lib/api';

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

const PAGE_SIZE = 10;

export default function MemoryPage() {
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [source, setSource] = useState<'all' | 'feedback'>('all');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [savingId, setSavingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<MemoryRecord | null>(null);
  const cancelDeleteRef = useRef<HTMLButtonElement>(null);
  const requestIdRef = useRef(0);

  const loadMemories = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    setRefreshing(true);
    try {
      const response = await api.memory.list({
        search: debouncedSearch || undefined,
        source: source === 'all' ? undefined : source,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      });
      if (requestIdRef.current !== requestId) return;
      setMemories(response.memories);
      setTotal(response.total);
      setError(null);
    } catch (err) {
      if (requestIdRef.current !== requestId) return;
      setError(err instanceof Error ? err.message : 'Failed to load memory');
    } finally {
      if (requestIdRef.current === requestId) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [debouncedSearch, source, page]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, source]);

  useEffect(() => {
    void loadMemories();
  }, [loadMemories]);

  function beginEdit(memory: MemoryRecord) {
    setEditingId(memory.id);
    setDraft(memory.content);
    setError(null);
  }

  async function saveEdit(memoryId: string) {
    const content = draft.trim();
    if (!content) {
      setError('Memory text cannot be empty.');
      return;
    }
    setSavingId(memoryId);
    try {
      const updated = await api.memory.update(memoryId, content);
      setMemories((current) =>
        current.map((memory) => (memory.id === memoryId ? updated : memory))
      );
      setEditingId(null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update memory');
    } finally {
      setSavingId(null);
    }
  }

  useEffect(() => {
    if (!pendingDelete) return;
    cancelDeleteRef.current?.focus();
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape' && !deletingId) setPendingDelete(null);
    }
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [pendingDelete, deletingId]);

  async function deleteMemory(memory: MemoryRecord) {
    setDeletingId(memory.id);
    try {
      await api.memory.delete(memory.id);
      setMemories((current) => current.filter((item) => item.id !== memory.id));
      setTotal((current) => Math.max(0, current - 1));
      if (memories.length === 1 && page > 1) setPage((current) => current - 1);
      if (editingId === memory.id) setEditingId(null);
      setPendingDelete(null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete memory');
    } finally {
      setDeletingId(null);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const firstItem = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const lastItem = Math.min(page * PAGE_SIZE, total);

  return (
    <div className="px-8 py-10 max-w-4xl">
      <PageHeader
        eyebrow="Personalization"
        title="Memory"
        actions={
          <button
            type="button"
            onClick={() => void loadMemories()}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-ink-600 text-stone-400 text-[13px] hover:border-ink-400 hover:text-stone-200 disabled:opacity-40 transition-colors"
          >
            <RefreshIcon size={13} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        }
      />

      <p className="text-stone-500 text-[13px] -mt-5 mb-6 max-w-2xl leading-5">
        These are durable preferences ResearchMind may use in future Chat and Research
        sessions. You stay in control: correct anything inaccurate or remove it entirely.
      </p>

      {error && (
        <div role="alert" className="mb-5 rounded-lg border border-red-900/70 bg-red-950/30 px-4 py-3 text-red-300 text-[13px]">
          {error}
        </div>
      )}

      <div className="mb-8 grid gap-3 sm:grid-cols-2">
        <div className="relative overflow-hidden rounded-xl border border-sage-900/80 bg-gradient-to-br from-sage-950/70 to-ink-800 px-5 py-4">
          <div className="absolute -right-7 -top-7 h-24 w-24 rounded-full bg-sage-700/10" />
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-sage-500">Personal memories</p>
          <p className="mt-2 font-display text-2xl text-stone-100">{loading ? '—' : total}</p>
          <p className="mt-1 text-[11px] text-stone-600">Available across Chat and Research</p>
        </div>
        <div className="rounded-xl border border-ink-600 bg-ink-800/40 px-5 py-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-stone-600">Your control</p>
          <p className="mt-2 text-[13px] font-medium text-stone-300">Review · Correct · Forget</p>
          <p className="mt-1 text-[11px] leading-4 text-stone-600">Changes apply to future eligible requests.</p>
        </div>
      </div>

      <section aria-labelledby="personal-memory-heading">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between" id="personal-memory-heading">
          <div>
            <SectionLabel count={total}>About you</SectionLabel>
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <Pill active={source === 'all'} onClick={() => setSource('all')}>All</Pill>
              <Pill active={source === 'feedback'} onClick={() => setSource('feedback')}>From feedback</Pill>
            </div>
          </div>
          <div className="relative w-full sm:w-72">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-600">
              <SearchIcon size={13} />
            </span>
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search your memories…"
              aria-label="Search personal memories"
              className="w-full rounded-lg border border-ink-600 bg-ink-800 py-2 pl-8 pr-3 text-[13px] text-stone-200 placeholder:text-stone-600 focus:border-sage-600 focus:outline-none"
            />
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center text-stone-600 text-[13px]">Loading memory…</div>
        ) : memories.length === 0 ? (
          <EmptyState
            title={search || source !== 'all' ? 'No matching memories' : 'Nothing remembered yet'}
            description={
              search || source !== 'all'
                ? 'Try a different search or clear the active filter.'
                : 'Explicit preferences you ask ResearchMind to remember will appear here.'
            }
            action={
              search || source !== 'all' ? (
                <button
                  type="button"
                  onClick={() => { setSearch(''); setSource('all'); }}
                  className="rounded-lg border border-ink-500 px-3 py-1.5 text-[12px] text-stone-300 hover:bg-ink-700"
                >
                  Clear filters
                </button>
              ) : undefined
            }
          />
        ) : (
          <ul className="space-y-3" role="list">
            {memories.map((memory) => {
              const editing = editingId === memory.id;
              const busy = savingId === memory.id || deletingId === memory.id;
              return (
                <li key={memory.id} className="group rounded-xl border border-ink-600 bg-ink-800/40 p-5 transition-colors hover:border-ink-500 hover:bg-ink-800/70">
                  <div className="mb-3 flex items-start gap-3">
                    <span className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg border border-sage-900 bg-sage-950/70 text-sage-400" aria-hidden="true">
                      <svg width="13" height="13" viewBox="0 0 15 15" fill="none">
                        <path d="M7.5 1.5a3 3 0 0 0-3 3v.2A2.75 2.75 0 0 0 3 9.75c0 1.52 1.23 2.75 2.75 2.75H7.5v-11zM7.5 3.25h1.75a2.25 2.25 0 0 1 1.58 3.85A2.75 2.75 0 0 1 10 12.5H7.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </span>
                    <div className="min-w-0 flex-1">
                  {editing ? (
                    <textarea
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                      rows={3}
                      maxLength={10000}
                      autoFocus
                      disabled={busy}
                      aria-label="Edit memory"
                      className="w-full resize-y rounded-lg border border-sage-800 bg-ink-900 px-3 py-2.5 text-stone-200 text-[14px] leading-6 placeholder:text-stone-700 focus:border-sage-600 disabled:opacity-60"
                    />
                  ) : (
                    <p className="text-stone-200 text-[14px] leading-6 whitespace-pre-wrap">
                      {memory.content}
                    </p>
                  )}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-3 border-t border-ink-700/80 pt-3">
                    <div className="flex items-center gap-2 text-[10px] font-mono text-stone-600">
                      <span className="rounded bg-sage-950 px-1.5 py-0.5 text-sage-400">PERSONAL</span>
                      <span title={memory.updated_at}>Updated {formatDate(memory.updated_at)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {editing ? (
                        <>
                          <button
                            type="button"
                            onClick={() => setEditingId(null)}
                            disabled={busy}
                            className="rounded-md px-2.5 py-1.5 text-stone-500 text-[12px] hover:bg-ink-700 hover:text-stone-200 disabled:opacity-40"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            onClick={() => void saveEdit(memory.id)}
                            disabled={busy || !draft.trim()}
                            className="rounded-md bg-sage-700 px-3 py-1.5 text-stone-100 text-[12px] hover:bg-sage-600 disabled:opacity-40"
                          >
                            {savingId === memory.id ? 'Saving…' : 'Save'}
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => beginEdit(memory)}
                            disabled={busy}
                            className="px-2.5 py-1.5 text-stone-500 text-[12px] hover:text-stone-200 disabled:opacity-40"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => setPendingDelete(memory)}
                            disabled={busy}
                            className="rounded-md px-2.5 py-1.5 text-stone-600 text-[12px] hover:bg-red-950/30 hover:text-red-400 disabled:opacity-40"
                          >
                            {deletingId === memory.id ? 'Deleting…' : 'Forget'}
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        {!loading && total > 0 && (
          <div className="mt-5 flex flex-col gap-3 border-t border-ink-700 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="font-mono text-[10px] text-stone-600">
              Showing {firstItem}–{lastItem} of {total}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page === 1 || refreshing}
                className="rounded-lg border border-ink-600 px-3 py-1.5 text-[12px] text-stone-400 hover:border-ink-400 hover:text-stone-200 disabled:cursor-not-allowed disabled:opacity-35"
              >
                Previous
              </button>
              <span className="min-w-16 text-center font-mono text-[10px] text-stone-500">
                {page} / {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                disabled={page >= totalPages || refreshing}
                className="rounded-lg border border-ink-600 px-3 py-1.5 text-[12px] text-stone-400 hover:border-ink-400 hover:text-stone-200 disabled:cursor-not-allowed disabled:opacity-35"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </section>

      {pendingDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !deletingId) setPendingDelete(null);
          }}
        >
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="forget-memory-title"
            aria-describedby="forget-memory-description"
            className="w-full max-w-md overflow-hidden rounded-2xl border border-ink-500 bg-ink-800 shadow-2xl shadow-black/60"
          >
            <div className="flex items-start gap-3 border-b border-ink-600 px-5 py-5">
              <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-red-950/70 text-red-400" aria-hidden="true">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M3 4.5h10M6 2.5h4l.5 2H5.5l.5-2zM4.5 4.5l.5 9h6l.5-9M6.75 7v4M9.25 7v4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </span>
              <div>
                <h2 id="forget-memory-title" className="font-display text-lg text-stone-100">Forget this memory?</h2>
                <p id="forget-memory-description" className="mt-1 text-[12px] leading-5 text-stone-500">
                  ResearchMind will stop using it in future requests. This action cannot be undone.
                </p>
              </div>
            </div>
            <div className="px-5 py-4">
              <p className="max-h-32 overflow-y-auto rounded-lg border border-ink-600 bg-ink-900/80 px-4 py-3 text-[13px] leading-5 text-stone-300">
                “{pendingDelete.content}”
              </p>
            </div>
            <div className="flex justify-end gap-2 border-t border-ink-600 bg-ink-900/40 px-5 py-4">
              <button
                ref={cancelDeleteRef}
                type="button"
                onClick={() => setPendingDelete(null)}
                disabled={Boolean(deletingId)}
                className="rounded-lg border border-ink-500 px-4 py-2 text-[12px] font-medium text-stone-300 hover:bg-ink-700 disabled:opacity-40"
              >
                Keep memory
              </button>
              <button
                type="button"
                onClick={() => void deleteMemory(pendingDelete)}
                disabled={Boolean(deletingId)}
                className="rounded-lg bg-red-800 px-4 py-2 text-[12px] font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deletingId ? 'Forgetting…' : 'Forget permanently'}
              </button>
            </div>
          </div>
        </div>
      )}

      <section className="mt-10" aria-labelledby="project-memory-heading">
        <div className="mb-3" id="project-memory-heading">
          <SectionLabel>Project memory</SectionLabel>
        </div>
        <div className="rounded-xl border border-dashed border-ink-600 bg-ink-800/20 px-5 py-5">
          <div className="flex items-center gap-2">
            <span className="rounded bg-amber-950/70 px-2 py-0.5 font-mono text-[10px] text-amber-400">M5</span>
            <p className="text-stone-300 text-[13px]">Available with Projects and Workspaces</p>
          </div>
          <p className="mt-2 max-w-2xl text-stone-600 text-[12px] leading-5">
            Project-specific facts and insights will appear here with the same edit and forget
            controls after project ownership and isolation are implemented.
          </p>
        </div>
      </section>
    </div>
  );
}
