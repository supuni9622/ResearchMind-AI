'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api, type Document } from '@/lib/api';
import { useActiveProject } from '@/hooks/use-active-project';
import { PageHeader } from '@/components/ui/page-header';
import { EmptyState } from '@/components/ui/empty-state';
import { RefreshIcon } from '@/components/ui/icons';
import { DocumentFilters } from '@/features/documents/components/document-filters';
import { DocumentRow } from '@/features/documents/components/document-row';
import { DocumentDetailsDrawer } from '@/features/documents/components/document-details-drawer';
import type { DocKind } from '@/features/documents/mock-meta';

const PAGE_SIZE = 10;
const SEARCH_DEBOUNCE_MS = 300;

export default function DocumentsPage() {
  const { activeProjectId } = useActiveProject();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [kindFilter, setKindFilter] = useState<DocKind | 'all'>('all');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [page, setPage] = useState(1);
  const requestIdRef = useRef(0);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [search]);

  // A kind/search/workspace change invalidates the current page's offset,
  // so jump back to page 1 rather than showing a (likely empty) stale page.
  useEffect(() => {
    setPage(1);
  }, [kindFilter, debouncedSearch, activeProjectId]);

  const loadDocuments = useCallback(
    async (opts: {
      page: number;
      kindFilter: DocKind | 'all';
      search: string;
      projectId: string | null;
    }) => {
      const requestId = ++requestIdRef.current;
      setFetching(true);
      try {
        const res = await api.documents.list({
          limit: PAGE_SIZE,
          offset: (opts.page - 1) * PAGE_SIZE,
          search: opts.search || undefined,
          kind: opts.kindFilter === 'all' ? undefined : opts.kindFilter,
          projectId: opts.projectId,
        });
        if (requestIdRef.current !== requestId) return;
        setDocuments(res.items);
        setTotal(res.total);
        setError(null);
      } catch (err) {
        if (requestIdRef.current !== requestId) return;
        setError(err instanceof Error ? err.message : 'Failed to load documents');
      } finally {
        if (requestIdRef.current === requestId) {
          setLoading(false);
          setFetching(false);
        }
      }
    },
    []
  );

  useEffect(() => {
    loadDocuments({ page, kindFilter, search: debouncedSearch, projectId: activeProjectId });
  }, [page, kindFilter, debouncedSearch, activeProjectId, loadDocuments]);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;
      setUploading(true);
      setError(null);
      try {
        await Promise.all(
          Array.from(files).map((f) => api.documents.upload(f, activeProjectId))
        );
        // Newly uploaded files sort first (newest first) — reset to an
        // unfiltered page 1 so the upload is immediately visible.
        setKindFilter('all');
        setSearch('');
        setDebouncedSearch('');
        if (page === 1) {
          await loadDocuments({
            page: 1,
            kindFilter: 'all',
            search: '',
            projectId: activeProjectId,
          });
        } else {
          setPage(1);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed');
      } finally {
        setUploading(false);
      }
    },
    [page, activeProjectId, loadDocuments]
  );

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const hasActiveFilter = kindFilter !== 'all' || debouncedSearch !== '';

  return (
    <div className="px-8 py-10 max-w-4xl">
      <PageHeader
        eyebrow="Knowledge Base"
        title="Documents"
        actions={
          <button
            type="button"
            onClick={() =>
              loadDocuments({ page, kindFilter, search: debouncedSearch, projectId: activeProjectId })
            }
            disabled={fetching}
            title="Refresh upload/processing status"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-ink-600 text-stone-400 text-[13px] hover:border-ink-400 hover:text-stone-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshIcon size={13} className={fetching ? 'animate-spin' : ''} />
            Refresh
          </button>
        }
      />
      <p className="text-stone-500 text-[13px] -mt-5 mb-6">
        Found a paper worth keeping in Chat? Download it and upload it here — Linear and Deep
        Research only draw on what&apos;s in this library.
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-10 mb-6 text-center transition-all duration-150 ${
          dragOver
            ? 'border-sage-500 bg-sage-800/20'
            : 'border-ink-500 hover:border-ink-400'
        }`}
      >
        {uploading ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-7 h-7 border-2 border-sage-800 border-t-sage-500 rounded-full animate-spin" />
            <p className="text-stone-500 text-sm">Uploading…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-ink-700 border border-ink-500 flex items-center justify-center">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                <path
                  d="M9 13V5M5 9l4-4 4 4M2 15h14"
                  stroke="#6B6560"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <div>
              <p className="text-stone-300 text-sm mb-1">
                Drop files here or{' '}
                <label className="text-sage-400 hover:text-sage-300 cursor-pointer transition-colors">
                  browse
                  <input
                    type="file"
                    className="sr-only"
                    multiple
                    accept=".pdf,.doc,.docx,.txt,.md,.png,.jpg,.jpeg,.webp,.gif"
                    onChange={(e) => handleFiles(e.target.files)}
                  />
                </label>
              </p>
              <p className="font-mono text-stone-600 text-[11px]">
                PDF · DOCX · TXT · MD · PNG · JPG · WEBP · GIF · up to 50 MB
              </p>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-5 px-4 py-3 rounded-lg border border-red-800/50 bg-red-900/20 text-red-400 text-[13px]">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-16 border border-dashed border-ink-600 rounded-xl">
          <p className="text-stone-600 text-sm">Loading documents…</p>
        </div>
      ) : total === 0 && !hasActiveFilter ? (
        <EmptyState
          title="No documents yet"
          description="Upload your first file above to start building your knowledge base."
        />
      ) : (
        <>
          <DocumentFilters
            active={kindFilter}
            onChange={setKindFilter}
            search={search}
            onSearchChange={setSearch}
          />

          {total === 0 ? (
            <EmptyState
              title="No documents match your filters"
              description="Try a different search term or clear the active filter."
            />
          ) : (
            <div className={`space-y-1.5 transition-opacity ${fetching ? 'opacity-60' : ''}`}>
              <div className="flex items-center px-3 pb-2 border-b border-ink-700 mb-1">
                <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase flex-1">
                  File
                </span>
                <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase w-20 text-right hidden md:inline">
                  Size
                </span>
                <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase w-20 text-right hidden lg:inline">
                  Chunks
                </span>
                <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase w-24 text-right">
                  Status
                </span>
                <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase w-28 text-right hidden sm:inline">
                  Date
                </span>
              </div>

              {documents.map((doc) => (
                <DocumentRow key={doc.id} doc={doc} onClick={() => setSelectedDoc(doc)} />
              ))}

              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-4">
                  <span className="font-mono text-stone-600 text-[11px]">
                    Page {page} of {totalPages}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1 || fetching}
                      className="px-3 py-1.5 rounded-lg border border-ink-600 text-stone-300 text-[13px] hover:border-ink-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages || fetching}
                      className="px-3 py-1.5 rounded-lg border border-ink-600 text-stone-300 text-[13px] hover:border-ink-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}

      <DocumentDetailsDrawer
        doc={selectedDoc}
        onClose={() => setSelectedDoc(null)}
        onDeleted={(documentId) => {
          setSelectedDoc(null);
          setDocuments((prev) => prev.filter((d) => d.id !== documentId));
          setTotal((prev) => Math.max(0, prev - 1));
        }}
      />
    </div>
  );
}
