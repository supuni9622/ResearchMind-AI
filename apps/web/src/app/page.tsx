import type { Metadata } from 'next';
import { LoginButton } from '@/components/auth/login-button';
import { Hero } from '@/components/landing/hero';
import { FeaturesSection } from '@/components/landing/features-section';
import { ArchitectureSection } from '@/components/landing/architecture-section';

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
      <header className="flex items-center justify-between px-8 py-5 border-b border-ink-600/60 sticky top-0 bg-ink-950/85 backdrop-blur-sm z-10">
        <div className="flex items-center gap-2.5">
          <LogoMark />
          <span className="text-stone-200 text-[13px] font-medium tracking-wide">
            ResearchMind
          </span>
        </div>
        <LoginButton variant="ghost" />
      </header>

      <main className="flex-1 flex flex-col">
        <Hero />
        <FeaturesSection />
        <ArchitectureSection />

        <section className="border-t border-ink-600/60 px-8 py-16 text-center">
          <p
            className="font-display text-stone-100 mb-6"
            style={{ fontSize: '1.75rem', fontVariationSettings: "'opsz' 40, 'SOFT' 0" }}
          >
            Start your first research session.
          </p>
          <LoginButton variant="primary" />
        </section>

        <footer className="border-t border-ink-600/60 px-8 py-5 flex items-center justify-between">
          <span className="font-mono text-stone-700 text-[11px]">
            © {new Date().getFullYear()} ResearchMind
          </span>
          <span className="font-mono text-stone-700 text-[11px]">Research Operating System</span>
        </footer>
      </main>
    </div>
  );
}
