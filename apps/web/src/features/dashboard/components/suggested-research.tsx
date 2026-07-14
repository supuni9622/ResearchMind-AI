import Link from 'next/link';
import { SectionLabel } from '@/components/ui/page-header';
import { SparklesIcon } from '@/components/ui/icons';
import { SUGGESTED_RESEARCH } from '@/features/dashboard/mock-data';

export function SuggestedResearch() {
  return (
    <div className="border border-ink-600 rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-ink-700">
        <SectionLabel>Suggested Research</SectionLabel>
      </div>
      <div className="divide-y divide-ink-700">
        {SUGGESTED_RESEARCH.map((s) => (
          <Link
            key={s.id}
            href={{ pathname: '/research', query: { q: s.prompt } }}
            className="group block px-5 py-3.5 hover:bg-ink-800/40 transition-colors duration-100"
          >
            <div className="flex items-start gap-2.5">
              <span className="text-amber-400 mt-0.5 flex-shrink-0">
                <SparklesIcon size={12} />
              </span>
              <div className="min-w-0">
                <p className="text-stone-300 text-[13px] leading-snug mb-1 group-hover:text-stone-100 transition-colors">
                  {s.prompt}
                </p>
                <p className="font-mono text-stone-700 text-[10px]">{s.reason}</p>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
