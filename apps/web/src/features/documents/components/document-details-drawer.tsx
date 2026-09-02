import { useEffect, useRef, useState } from 'react';
import { api, type Document } from '@/lib/api';
import { Drawer } from '@/components/ui/drawer';
import { Badge } from '@/components/ui/badge';
import { SectionLabel } from '@/components/ui/page-header';
import { TagIcon, LayersIcon, DatabaseIcon, FileTextIcon, MessageIcon, AlertIcon } from '@/components/ui/icons';
import { getDocumentMeta, getDocKind, DOC_KIND_LABEL } from '@/features/documents/mock-meta';
import { RECENT_SESSIONS } from '@/features/dashboard/mock-data';

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

const STATUS_TONE = {
  pending: 'neutral',
  processing: 'amber',
  completed: 'sage',
  failed: 'red',
} as const;

export function DocumentDetailsDrawer({
  doc,
  onClose,
  onDeleted,
}: {
  doc: Document | null;
  onClose: () => void;
  /** Called once the document is actually deleted server-side (Qdrant
   * vectors + S3 artifacts + the Postgres row) -- the caller closes the
   * drawer and removes the row from its own list state. */
  onDeleted: (documentId: string) => void;
}) {
  const meta = doc ? getDocumentMeta(doc) : null;
  const kind = doc ? getDocKind(doc) : null;
  const sessions = RECENT_SESSIONS.slice(0, 2);

  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const dialogCancelRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const dialogInvokerRef = useRef<HTMLElement | null>(null);

  // A different document selected while a confirm dialog is open (the
  // drawer stays mounted across selections) shouldn't carry over stale
  // dialog/error state from the previous one.
  useEffect(() => {
    setConfirmingDelete(false);
    setDeleteError(null);
  }, [doc?.id]);

  // Mirrors `memory/page.tsx`'s alertdialog focus-trap: focus the Cancel
  // button on open, trap Tab within the dialog, Escape cancels, restore
  // focus to whatever opened it on close.
  useEffect(() => {
    if (!confirmingDelete) return;
    dialogInvokerRef.current = document.activeElement as HTMLElement | null;
    dialogCancelRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !deleting) {
        setConfirmingDelete(false);
        return;
      }
      if (event.key === 'Tab' && dialogRef.current) {
        const controls = Array.from(
          dialogRef.current.querySelectorAll<HTMLElement>('button:not(:disabled)')
        );
        if (!controls.length) return;
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      dialogInvokerRef.current?.focus();
    };
  }, [confirmingDelete, deleting]);

  async function handleConfirmDelete() {
    if (!doc) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.documents.delete(doc.id);
      onDeleted(doc.id);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Could not delete this document.');
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Drawer open={doc != null} onClose={onClose} eyebrow="Document" title={doc?.filename ?? ''}>
      {doc && meta && kind && (
        <div className="space-y-6">
          <div>
            <Badge tone={STATUS_TONE[doc.processing_status]}>{doc.processing_status}</Badge>
          </div>

          {doc.processing_status === 'failed' && doc.processing_error && (
            <div>
              <SectionLabel>Error</SectionLabel>
              <div className="mt-3 flex items-start gap-2.5 border border-red-900/50 bg-red-900/10 rounded-lg p-3">
                <span className="text-red-400 mt-0.5"><AlertIcon size={13} /></span>
                <p className="text-red-300 text-[12.5px] leading-relaxed break-words">
                  {doc.processing_error}
                </p>
              </div>
            </div>
          )}

          <div>
            <SectionLabel>Metadata</SectionLabel>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <div className="border border-ink-600 rounded-lg p-3">
                <p className="font-mono text-stone-600 text-[10px] uppercase tracking-widest mb-1">
                  Type
                </p>
                <p className="text-stone-200 text-[13px]">{DOC_KIND_LABEL[kind]}</p>
              </div>
              <div className="border border-ink-600 rounded-lg p-3">
                <p className="font-mono text-stone-600 text-[10px] uppercase tracking-widest mb-1">
                  Size
                </p>
                <p className="text-stone-200 text-[13px]">{formatBytes(doc.size_bytes)}</p>
              </div>
              <div className="border border-ink-600 rounded-lg p-3">
                <p className="font-mono text-stone-600 text-[10px] uppercase tracking-widest mb-1">
                  Created
                </p>
                <p className="text-stone-200 text-[13px]">
                  {doc.created_at ? formatDate(doc.created_at) : '—'}
                </p>
              </div>
              <div className="border border-ink-600 rounded-lg p-3">
                <p className="font-mono text-stone-600 text-[10px] uppercase tracking-widest mb-1">
                  Pages
                </p>
                <p className="text-stone-200 text-[13px]">{meta.pageCount}</p>
              </div>
            </div>
          </div>

          <div>
            <SectionLabel>Statistics</SectionLabel>
            <div className="mt-3 space-y-2">
              <div className="flex items-center gap-2.5 border border-ink-600 rounded-lg px-3 py-2.5">
                <span className="text-stone-600"><LayersIcon size={13} /></span>
                <span className="flex-1 text-stone-300 text-[12.5px]">Chunks</span>
                <span className="font-mono text-stone-400 text-[12px]">{meta.chunkCount}</span>
              </div>
              <div className="flex items-center gap-2.5 border border-ink-600 rounded-lg px-3 py-2.5">
                <span className="text-stone-600"><DatabaseIcon size={13} /></span>
                <span className="flex-1 text-stone-300 text-[12.5px]">Embeddings</span>
                <span className="font-mono text-stone-400 text-[12px]">{meta.embeddingCount}</span>
              </div>
            </div>
          </div>

          <div>
            <SectionLabel>Tags</SectionLabel>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {meta.tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-ink-800 border border-ink-600 text-stone-400 text-[11px]"
                >
                  <TagIcon size={10} />
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <div>
            <SectionLabel>Preview</SectionLabel>
            <div className="mt-3 border border-ink-600 rounded-lg p-4 flex items-center gap-3 text-stone-600">
              <FileTextIcon size={16} />
              <p className="text-[12.5px]">
                Inline document preview will appear here once the viewer is wired up.
              </p>
            </div>
          </div>

          <div>
            <SectionLabel>Research Sessions</SectionLabel>
            <div className="mt-3 space-y-1.5">
              {sessions.map((s) => (
                <div
                  key={s.id}
                  className="flex items-center gap-2.5 border border-ink-600 rounded-lg px-3 py-2.5"
                >
                  <span className="text-stone-600"><MessageIcon size={12} /></span>
                  <span className="flex-1 text-stone-300 text-[12.5px]">{s.title}</span>
                  <span className="font-mono text-stone-700 text-[10px]">
                    {s.questionCount} questions
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-2 border-t border-ink-700">
            <button
              type="button"
              onClick={() => setConfirmingDelete(true)}
              className="w-full px-3 py-2 rounded-lg text-[12.5px] text-stone-600 hover:bg-red-950/30 hover:text-red-400 transition-colors"
            >
              Delete document
            </button>
          </div>
        </div>
      )}

      {doc && confirmingDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !deleting) setConfirmingDelete(false);
          }}
        >
          <div
            ref={dialogRef}
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="delete-document-title"
            className="w-full max-w-md overflow-hidden rounded-2xl border border-ink-500 bg-ink-800 shadow-2xl"
          >
            <div className="border-b border-ink-600 px-5 py-5">
              <h2 id="delete-document-title" className="font-display text-lg text-stone-100">
                Delete this document?
              </h2>
              <p className="mt-1 text-[12px] leading-5 text-stone-500">
                This permanently removes “{doc.filename}” and its indexed content. Research
                answers can no longer draw on it. There is no undo.
              </p>
            </div>
            {deleteError && (
              <div role="alert" className="px-5 pt-4">
                <p className="rounded-lg border border-red-900/60 bg-red-950/20 px-3 py-3 text-[12px] leading-5 text-red-200">
                  {deleteError}
                </p>
              </div>
            )}
            <div className="flex justify-end gap-2 border-t border-ink-600 px-5 py-4">
              <button
                ref={dialogCancelRef}
                type="button"
                disabled={deleting}
                onClick={() => setConfirmingDelete(false)}
                className="rounded-lg border border-ink-500 px-4 py-2 text-[12px] text-stone-300 disabled:opacity-40"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleting}
                onClick={() => void handleConfirmDelete()}
                className="rounded-lg bg-red-800 px-4 py-2 text-[12px] text-white disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Delete permanently'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Drawer>
  );
}
