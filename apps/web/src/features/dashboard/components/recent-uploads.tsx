import Link from 'next/link';
import type { Document } from '@/lib/api';
import { SectionLabel } from '@/components/ui/page-header';
import { FileTextIcon } from '@/components/ui/icons';
import { Badge } from '@/components/ui/badge';

const STATUS_TONE = {
  pending: 'neutral',
  processing: 'amber',
  completed: 'sage',
  failed: 'red',
} as const;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function RecentUploads({ documents, loading }: { documents: Document[]; loading: boolean }) {
  const recent = documents.slice(0, 5);

  return (
    <div className="border border-ink-600 rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-ink-700 flex items-center justify-between">
        <SectionLabel count={documents.length}>Recent Uploads</SectionLabel>
        <Link
          href="/documents"
          className="font-mono text-stone-600 hover:text-sage-400 text-[10px] transition-colors"
        >
          view all
        </Link>
      </div>

      {loading ? (
        <div className="px-5 py-6 text-center">
          <p className="text-stone-700 text-[12px]">Loading…</p>
        </div>
      ) : recent.length === 0 ? (
        <div className="px-5 py-6 text-center">
          <p className="text-stone-700 text-[12px]">No documents uploaded yet.</p>
        </div>
      ) : (
        <div className="divide-y divide-ink-700">
          {recent.map((doc) => (
            <div key={doc.id} className="flex items-center gap-3 px-5 py-3">
              <span className="text-stone-700 flex-shrink-0">
                <FileTextIcon size={13} />
              </span>
              <p className="flex-1 min-w-0 text-stone-300 text-[12.5px] truncate">
                {doc.filename}
              </p>
              <Badge tone={STATUS_TONE[doc.processing_status]}>{doc.processing_status}</Badge>
              <span className="font-mono text-stone-700 text-[10px] flex-shrink-0 w-12 text-right">
                {doc.created_at ? formatDate(doc.created_at) : '—'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
