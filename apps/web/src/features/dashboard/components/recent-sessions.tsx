import Link from 'next/link';
import { SectionLabel } from '@/components/ui/page-header';
import { ChevronRightIcon, MessageIcon, FileTextIcon } from '@/components/ui/icons';
import { RECENT_SESSIONS } from '@/features/dashboard/mock-data';

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const hours = Math.round(diffMs / 3_600_000);
  if (hours < 1) return 'just now';
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function RecentSessions() {
  return (
    <div className="border border-ink-600 rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-ink-700 flex items-center justify-between">
        <SectionLabel count={RECENT_SESSIONS.length}>Research Sessions</SectionLabel>
        <Link
          href="/research"
          className="font-mono text-stone-600 hover:text-sage-400 text-[10px] transition-colors"
        >
          view all
        </Link>
      </div>
      <div className="divide-y divide-ink-700">
        {RECENT_SESSIONS.map((session) => (
          <Link
            key={session.id}
            href={`/research?session=${session.id}`}
            className="group flex items-center gap-3 px-5 py-3.5 hover:bg-ink-800/40 transition-colors duration-100"
          >
            <div className="flex-1 min-w-0">
              <p className="text-stone-200 text-[13px] font-medium mb-1 truncate">
                {session.title}
              </p>
              <div className="flex items-center gap-3 text-stone-600">
                <span className="flex items-center gap-1 font-mono text-[10px]">
                  <MessageIcon size={11} />
                  {session.questionCount}
                </span>
                <span className="flex items-center gap-1 font-mono text-[10px]">
                  <FileTextIcon size={11} />
                  {session.documentCount}
                </span>
                <span className="font-mono text-[10px]">{relativeTime(session.updatedAt)}</span>
              </div>
            </div>
            <span className="text-stone-700 group-hover:text-sage-500 transition-colors flex-shrink-0">
              <ChevronRightIcon />
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
