import Link from 'next/link';
import { SectionLabel } from '@/components/ui/page-header';
import { RECENT_QUESTIONS } from '@/features/dashboard/mock-data';

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const hours = Math.round(diffMs / 3_600_000);
  if (hours < 1) return 'just now';
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function RecentQuestions() {
  return (
    <div className="border border-ink-600 rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-ink-700">
        <SectionLabel count={RECENT_QUESTIONS.length}>Recent Questions</SectionLabel>
      </div>
      <div className="divide-y divide-ink-700">
        {RECENT_QUESTIONS.map((q) => (
          <Link
            key={q.id}
            href="/research"
            className="block px-5 py-3.5 hover:bg-ink-800/40 transition-colors duration-100"
          >
            <p className="text-stone-300 text-[13px] leading-snug mb-1.5 line-clamp-2">
              {q.question}
            </p>
            <div className="flex items-center gap-2 font-mono text-[10px] text-stone-600">
              <span className="text-sage-500">{q.sessionTitle}</span>
              <span>·</span>
              <span>{relativeTime(q.askedAt)}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
