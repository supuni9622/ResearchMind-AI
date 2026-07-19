'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  api,
  type Document,
  type DocumentKnowledgeStats,
  type GenerationUsageSummary,
} from '@/lib/api';
import { PageHeader } from '@/components/ui/page-header';
import { SearchIcon, UploadIcon } from '@/components/ui/icons';
import { KnowledgeBaseStats } from '@/features/dashboard/components/kb-stats';
import { RecentSessions } from '@/features/dashboard/components/recent-sessions';
import { RecentQuestions } from '@/features/dashboard/components/recent-questions';
import { PlatformHealth } from '@/features/dashboard/components/platform-health';
import { SuggestedResearch } from '@/features/dashboard/components/suggested-research';
import { RecentUploads } from '@/features/dashboard/components/recent-uploads';
import type {
  DashboardQuestion,
  DashboardResearchSession,
  DashboardSuggestion,
} from '@/features/dashboard/types';

export default function DashboardPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [knowledgeStats, setKnowledgeStats] = useState<DocumentKnowledgeStats | null>(null);
  const [usageSummary, setUsageSummary] = useState<GenerationUsageSummary | null>(null);
  const [researchSessions, setResearchSessions] = useState<DashboardResearchSession[]>([]);
  const [researchSessionCount, setResearchSessionCount] = useState(0);
  const [recentQuestions, setRecentQuestions] = useState<DashboardQuestion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadDashboard() {
      const [docsResult, knowledgeStatsResult, usageResult, researchResult, chatResult] = await Promise.allSettled([
        api.documents.list(),
        api.documents.stats(),
        api.usage.summary(),
        api.research.listConversations(),
        api.chat.listConversations(),
      ]);

      if (cancelled) return;

      const docs = docsResult.status === 'fulfilled' ? docsResult.value : [];
      const stats = knowledgeStatsResult.status === 'fulfilled' ? knowledgeStatsResult.value : null;
      const usage = usageResult.status === 'fulfilled' ? usageResult.value : null;
      const allResearchConversations =
        researchResult.status === 'fulfilled' ? researchResult.value.conversations : [];
      const researchConversations = allResearchConversations.slice(0, 3);
      const chatConversations =
        chatResult.status === 'fulfilled' ? chatResult.value.conversations.slice(0, 3) : [];

      const [researchDetails, chatDetails] = await Promise.all([
        Promise.all(
          researchConversations.map(async (conversation) => {
            const detail = await api.research.getConversation(conversation.conversation_id);
            return { conversation, detail };
          })
        ),
        Promise.all(
          chatConversations.map(async (conversation) => {
            const detail = await api.chat.getConversation(conversation.conversation_id);
            return { conversation, detail };
          })
        ),
      ]).catch(() => [[], []] as const);

      if (cancelled) return;

      setDocuments(docs);
      setKnowledgeStats(stats);
      setUsageSummary(usage);
      setResearchSessionCount(allResearchConversations.length);
      setResearchSessions(
        researchDetails.map(({ conversation, detail }) => ({
          id: conversation.conversation_id,
          title: conversation.title ?? 'Untitled research',
          questionCount: detail.turns.length,
          documentCount: new Set(
            detail.turns.flatMap((turn) => turn.sources.map((source) => source.document_id))
          ).size,
          updatedAt: conversation.updated_at,
        }))
      );
      setRecentQuestions(
        chatDetails
          .flatMap(({ conversation, detail }) =>
            detail.messages
              .filter((message) => message.role === 'user')
              .map((message) => ({
                id: message.id,
                question: message.content,
                conversationTitle: conversation.title ?? 'New chat',
                askedAt: message.created_at,
                conversationId: conversation.conversation_id,
              }))
          )
          .sort((left, right) => Date.parse(right.askedAt) - Date.parse(left.askedAt))
          .slice(0, 3)
      );
      setLoading(false);
    }

    void loadDashboard().catch(() => {
      if (!cancelled) setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const suggestions: DashboardSuggestion[] = documents.slice(0, 3).map((document, index) => ({
    id: document.id,
    prompt:
      index === 0
        ? `Summarize the key findings in ${document.filename}.`
        : `What does ${document.filename} add to the document library?`,
    reason: 'Based on an uploaded document',
  }));

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
        <KnowledgeBaseStats
          documentCount={documents.length}
          indexedChunkCount={knowledgeStats?.indexed_chunk_count ?? null}
          embeddingCount={knowledgeStats?.embedding_count ?? null}
          researchSessionCount={researchSessionCount}
          monthCostUsd={usageSummary?.month_cost_usd ?? null}
          totalCostUsd={usageSummary?.total_cost_usd ?? null}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-5">
          <RecentSessions sessions={researchSessions} />
          <RecentQuestions questions={recentQuestions} />
        </div>
        <div className="space-y-5">
          <PlatformHealth />
          <SuggestedResearch suggestions={suggestions} />
          <RecentUploads documents={documents} loading={loading} />
        </div>
      </div>
    </div>
  );
}
