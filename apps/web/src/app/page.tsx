import type { Metadata } from 'next';
import { LoginButton } from '@/components/auth/login-button';

export const metadata: Metadata = {
  title: 'ResearchMind — AI Research Intelligence',
  description:
    'Upload your documents. Ask precise questions. Get cited answers grounded in your sources.',
};

function LogoMark() {
  return (
    <div className="w-7 h-7 rounded-md bg-sage-600 flex items-center justify-center flex-shrink-0">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
        <path
          d="M1 1h5v5H1zM8 1h5v5H8zM1 8h5v5H1zM10.5 8a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5z"
          fill="white"
        />
      </svg>
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-ink-950 flex flex-col">
      <header className="flex items-center justify-between px-8 py-5 border-b border-ink-600/60">
        <div className="flex items-center gap-2.5">
          <LogoMark />
          <span className="text-stone-200 text-[13px] font-medium tracking-wide">
            ResearchMind
          </span>
        </div>
        <LoginButton variant="ghost" />
      </header>

      <main className="flex-1 flex flex-col">
        <section className="flex-1 flex flex-col items-center justify-center px-6 py-24 text-center">
          <div className="max-w-3xl mx-auto">
            <p className="font-mono text-sage-500 text-[11px] tracking-[0.22em] uppercase mb-8">
              AI Research Intelligence Platform
            </p>

            <h1
              className="font-display text-stone-100 leading-[1.04] tracking-tight mb-6 text-balance"
              style={{
                fontSize: 'clamp(2.5rem, 7.5vw, 5.25rem)',
                fontVariationSettings: "'opsz' 72, 'SOFT' 0, 'WONK' 0",
              }}
            >
              Research that thinks
              <br />
              <span className="text-sage-400">with you.</span>
            </h1>

            <p className="text-stone-400 text-lg leading-relaxed max-w-md mx-auto mb-12">
              Upload your documents. Ask precise questions. Get answers
              grounded in your sources, with citations you can verify.
            </p>

            <LoginButton variant="primary" />
          </div>
        </section>

        <section className="border-t border-ink-600/60 px-8 py-5">
          <div className="max-w-3xl mx-auto flex flex-wrap items-center justify-center gap-x-10 gap-y-3">
            {[
              { label: 'Upload', sub: 'PDF · DOCX · TXT' },
              { label: 'Query', sub: 'Natural language' },
              { label: 'Cite', sub: 'Source-grounded' },
              { label: 'Synthesize', sub: 'Cross-document' },
            ].map(({ label, sub }) => (
              <div key={label} className="flex items-center gap-2">
                <span className="text-stone-200 text-sm font-medium">{label}</span>
                <span className="text-ink-500">·</span>
                <span className="font-mono text-stone-500 text-[11px]">{sub}</span>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
