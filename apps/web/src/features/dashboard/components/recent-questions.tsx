import Link from 'next/link';
import { SectionLabel } from '@/components/ui/page-header';
import type { DashboardQuestion } from '@/features/dashboard/types';

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const hours = Math.round(diffMs / 3_600_000);
  if (hours < 1) return 'just now';
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function RecentQuestions({ questions }: { questions: DashboardQuestion[] }) {
  return (
    <div className="border border-ink-600 rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-ink-700">
        <SectionLabel count={questions.length}>Recent Questions</SectionLabel>
      </div>
      {questions.length === 0 ? (
        <div className="px-5 py-6 text-center text-stone-700 text-[12px]">
          No chat questions yet.
        </div>
      ) : (
      <div className="divide-y divide-ink-700">
        {questions.map((q) => (
          <Link
            key={q.id}
            href={`/chat?conversation=${q.conversationId}`}
            className="block px-5 py-3.5 hover:bg-ink-800/40 transition-colors duration-100"
          >
            <p className="text-stone-300 text-[13px] leading-snug mb-1.5 line-clamp-2">
              {q.question}
            </p>
            <div className="flex items-center gap-2 font-mono text-[10px] text-stone-600">
              <span className="text-sage-500">{q.conversationTitle}</span>
              <span>·</span>
              <span>{relativeTime(q.askedAt)}</span>
            </div>
          </Link>
        ))}
      </div>
      )}
    </div>
  );
}
