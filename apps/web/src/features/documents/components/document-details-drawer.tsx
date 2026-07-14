import type { Document } from '@/lib/api';
import { Drawer } from '@/components/ui/drawer';
import { Badge } from '@/components/ui/badge';
import { SectionLabel } from '@/components/ui/page-header';
import { TagIcon, LayersIcon, DatabaseIcon, FileTextIcon, MessageIcon } from '@/components/ui/icons';
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
}: {
  doc: Document | null;
  onClose: () => void;
}) {
  const meta = doc ? getDocumentMeta(doc) : null;
  const kind = doc ? getDocKind(doc) : null;
  const sessions = RECENT_SESSIONS.slice(0, 2);

  return (
    <Drawer open={doc != null} onClose={onClose} eyebrow="Document" title={doc?.filename ?? ''}>
      {doc && meta && kind && (
        <div className="space-y-6">
          <div>
            <Badge tone={STATUS_TONE[doc.processing_status]}>{doc.processing_status}</Badge>
          </div>

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
        </div>
      )}
    </Drawer>
  );
}
