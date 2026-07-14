'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, type Document } from '@/lib/api';
import { PageHeader } from '@/components/ui/page-header';
import { SearchIcon, UploadIcon } from '@/components/ui/icons';
import { KnowledgeBaseStats } from '@/features/dashboard/components/kb-stats';
import { RecentSessions } from '@/features/dashboard/components/recent-sessions';
import { RecentQuestions } from '@/features/dashboard/components/recent-questions';
import { PlatformHealth } from '@/features/dashboard/components/platform-health';
import { SuggestedResearch } from '@/features/dashboard/components/suggested-research';
import { RecentUploads } from '@/features/dashboard/components/recent-uploads';

export default function DashboardPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.documents
      .list()
      .then((docs) => {
        if (!cancelled) setDocuments(docs);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="px-8 py-10 max-w-6xl">
      <PageHeader eyebrow="Research Workspace" title="Overview" />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
        <Link
          href="/research"
          className="group border border-ink-600 rounded-xl p-5 hover:border-sage-700 hover:bg-ink-800/40 transition-all duration-150"
        >
          <div className="flex items-start justify-between mb-5">
            <div className="w-9 h-9 rounded-lg bg-sage-800/60 border border-sage-700/50 flex items-center justify-center text-sage-400">
              <SearchIcon size={15} />
            </div>
            <span className="text-stone-600 group-hover:text-sage-500 transition-colors">→</span>
          </div>
          <h2 className="text-stone-100 text-sm font-medium mb-1">Start Research</h2>
          <p className="text-stone-500 text-[13px]">
            Ask questions across your document library
          </p>
        </Link>

        <Link
          href="/documents"
          className="group border border-ink-600 rounded-xl p-5 hover:border-ink-400 hover:bg-ink-800/40 transition-all duration-150"
        >
          <div className="flex items-start justify-between mb-5">
            <div className="w-9 h-9 rounded-lg bg-ink-700 border border-ink-500/60 flex items-center justify-center text-stone-400">
              <UploadIcon size={15} />
            </div>
            <span className="text-stone-600 group-hover:text-stone-400 transition-colors">→</span>
          </div>
          <h2 className="text-stone-100 text-sm font-medium mb-1">Upload Documents</h2>
          <p className="text-stone-500 text-[13px]">Add PDFs, Word documents, or plain text</p>
        </Link>
      </div>

      <div className="mb-8">
        <KnowledgeBaseStats documentCount={documents.length} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-5">
          <RecentSessions />
          <RecentQuestions />
        </div>
        <div className="space-y-5">
          <PlatformHealth />
          <SuggestedResearch />
          <RecentUploads documents={documents} loading={loading} />
        </div>
      </div>
    </div>
  );
}
