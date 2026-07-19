import type { Document } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { FileTextIcon, AlertIcon } from '@/components/ui/icons';
import { getDocumentMeta } from '@/features/documents/mock-meta';

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

const STATUS_TONE = {
  pending: 'neutral',
  processing: 'amber',
  completed: 'sage',
  failed: 'red',
} as const;

export function DocumentRow({ doc, onClick }: { doc: Document; onClick: () => void }) {
  const meta = getDocumentMeta(doc);

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border border-ink-700 hover:border-ink-500 hover:bg-ink-800/30 transition-all duration-100 text-left"
    >
      <div className="w-7 h-7 rounded bg-ink-700 border border-ink-600 flex items-center justify-center flex-shrink-0 text-stone-600">
        <FileTextIcon size={12} />
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-stone-200 text-[13px] truncate">{doc.filename}</p>
        <p className="font-mono text-stone-600 text-[10px]">{doc.content_type}</p>
      </div>

      <span className="font-mono text-stone-500 text-[11px] w-20 text-right flex-shrink-0 hidden md:inline">
        {formatBytes(doc.size_bytes)}
      </span>

      <span className="font-mono text-stone-500 text-[11px] w-20 text-right flex-shrink-0 hidden lg:inline">
        {meta.chunkCount} chunks
      </span>

      <span
        className="w-24 flex-shrink-0 flex items-center justify-center gap-1"
        title={doc.processing_status === 'failed' ? doc.processing_error ?? undefined : undefined}
      >
        {doc.processing_status === 'failed' && doc.processing_error && (
          <AlertIcon size={11} className="text-red-400 flex-shrink-0" />
        )}
        <Badge tone={STATUS_TONE[doc.processing_status]} className="text-center">
          {doc.processing_status}
        </Badge>
      </span>

      <span className="font-mono text-stone-600 text-[11px] flex-shrink-0 w-28 text-right hidden sm:inline">
        {doc.created_at ? formatDate(doc.created_at) : '—'}
      </span>
    </button>
  );
}
