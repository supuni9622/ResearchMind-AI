'use client';

import { useCallback, useState } from 'react';
import { api, type Document } from '@/lib/api';

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-ink-700 text-stone-400',
  processing: 'bg-amber-500/20 text-amber-400',
  completed: 'bg-sage-800/60 text-sage-400',
  failed: 'bg-red-900/30 text-red-400',
};

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="px-8 py-10 max-w-4xl">
      <header className="mb-8">
        <p className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase mb-2">
          Knowledge Base
        </p>
        <h1
          className="font-display text-stone-100 leading-tight"
          style={{
            fontSize: '2.25rem',
            fontVariationSettings: "'opsz' 48, 'SOFT' 0, 'WONK' 0",
          }}
        >
          Documents
        </h1>
      </header>

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

      {documents.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-ink-600 rounded-xl">
          <p className="text-stone-600 text-sm">
            No documents yet — upload your first file above.
          </p>
        </div>
      ) : (
        <div className="space-y-1.5">
          <div className="flex items-center px-3 pb-2 border-b border-ink-700 mb-1">
            <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase flex-1">
              File
            </span>
            <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase w-20 text-right">
              Size
            </span>
            <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase w-24 text-right">
              Status
            </span>
            <span className="font-mono text-stone-600 text-[10px] tracking-widest uppercase w-28 text-right">
              Date
            </span>
          </div>

          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-ink-700 hover:border-ink-500 hover:bg-ink-800/30 transition-all duration-100"
            >
              <div className="w-7 h-7 rounded bg-ink-700 border border-ink-600 flex items-center justify-center flex-shrink-0">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                  <path
                    d="M7 1H2a.75.75 0 0 0-.75.75v8.5c0 .414.336.75.75.75h8a.75.75 0 0 0 .75-.75V4.5L7 1z"
                    stroke="#6B6560"
                    strokeWidth="1.1"
                    strokeLinejoin="round"
                  />
                  <path d="M7 1v3.5h3.75" stroke="#6B6560" strokeWidth="1.1" strokeLinejoin="round" />
                </svg>
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-stone-200 text-[13px] truncate">{doc.filename}</p>
                <p className="font-mono text-stone-600 text-[10px]">{doc.content_type}</p>
              </div>

              <span className="font-mono text-stone-500 text-[11px] w-20 text-right flex-shrink-0">
                {formatBytes(doc.size_bytes)}
              </span>

              <span
                className={`font-mono text-[10px] px-2 py-0.5 rounded-full flex-shrink-0 w-24 text-center ${
                  STATUS_STYLES[doc.processing_status] ?? 'bg-ink-700 text-stone-500'
                }`}
              >
                {doc.processing_status}
              </span>

              <span className="font-mono text-stone-600 text-[11px] flex-shrink-0 w-28 text-right">
                {doc.created_at ? formatDate(doc.created_at) : '—'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
