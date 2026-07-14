'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { api, type Document } from '@/lib/api';
import { PageHeader } from '@/components/ui/page-header';
import { EmptyState } from '@/components/ui/empty-state';
import { DocumentFilters } from '@/features/documents/components/document-filters';
import { DocumentRow } from '@/features/documents/components/document-row';
import { DocumentDetailsDrawer } from '@/features/documents/components/document-details-drawer';
import { getDocKind, type DocKind } from '@/features/documents/mock-meta';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [kindFilter, setKindFilter] = useState<DocKind | 'all'>('all');
  const [search, setSearch] = useState('');
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);

  useEffect(() => {
    let cancelled = false;

    api.documents
      .list()
      .then((docs) => {
        if (!cancelled) setDocuments(docs);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load documents');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const results = await Promise.all(Array.from(files).map((f) => api.documents.upload(f)));
      setDocuments((prev) => [...results, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, []);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }

  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      if (kindFilter !== 'all' && getDocKind(doc) !== kindFilter) return false;
      if (search && !doc.filename.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [documents, kindFilter, search]);

  return (
    <div className="px-8 py-10 max-w-4xl">
      <PageHeader eyebrow="Knowledge Base" title="Documents" />

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
                    accept=".pdf,.doc,.docx,.txt,.md"
                    onChange={(e) => handleFiles(e.target.files)}
                  />
                </label>
              </p>
              <p className="font-mono text-stone-600 text-[11px]">
                PDF · DOCX · TXT · MD · up to 50 MB
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
      ) : documents.length === 0 ? (
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

          {filteredDocuments.length === 0 ? (
            <EmptyState
              title="No documents match your filters"
              description="Try a different search term or clear the active filter."
            />
          ) : (
            <div className="space-y-1.5">
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

              {filteredDocuments.map((doc) => (
                <DocumentRow key={doc.id} doc={doc} onClick={() => setSelectedDoc(doc)} />
              ))}
            </div>
          )}
        </>
      )}

      <DocumentDetailsDrawer doc={selectedDoc} onClose={() => setSelectedDoc(null)} />
    </div>
  );
}
