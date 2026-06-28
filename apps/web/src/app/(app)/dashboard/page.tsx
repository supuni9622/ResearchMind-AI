import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = { title: 'Dashboard' };

export default function DashboardPage() {
  return (
    <div className="px-8 py-10 max-w-4xl">
      <header className="mb-10">
        <p className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase mb-2">
          Overview
        </p>
        <h1
          className="font-display text-stone-100 leading-tight"
          style={{
            fontSize: '2.25rem',
            fontVariationSettings: "'opsz' 48, 'SOFT' 0, 'WONK' 0",
          }}
        >
          Dashboard
        </h1>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-10">
        <Link
          href="/research"
          className="group border border-ink-600 rounded-xl p-5 hover:border-sage-700 hover:bg-ink-800/40 transition-all duration-150"
        >
          <div className="flex items-start justify-between mb-5">
            <div className="w-9 h-9 rounded-lg bg-sage-800/60 border border-sage-700/50 flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <circle cx="7" cy="7" r="5.5" stroke="#82A695" strokeWidth="1.25" />
                <path d="M11 11l3.5 3.5" stroke="#82A695" strokeWidth="1.25" strokeLinecap="round" />
              </svg>
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
            <div className="w-9 h-9 rounded-lg bg-ink-700 border border-ink-500/60 flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path
                  d="M9 1H3a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V6L9 1z"
                  stroke="#9B9589"
                  strokeWidth="1.25"
                  strokeLinejoin="round"
                />
                <path d="M9 1v5h5" stroke="#9B9589" strokeWidth="1.25" strokeLinejoin="round" />
                <path
                  d="M5 9h6M5 11.5h4"
                  stroke="#9B9589"
                  strokeWidth="1.25"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <span className="text-stone-600 group-hover:text-stone-400 transition-colors">→</span>
          </div>
          <h2 className="text-stone-100 text-sm font-medium mb-1">Upload Documents</h2>
          <p className="text-stone-500 text-[13px]">Add PDFs, Word documents, or plain text</p>
        </Link>
      </div>

      <div className="border border-ink-600 rounded-xl p-5">
        <h2 className="text-stone-400 text-[12px] font-medium uppercase tracking-widest font-mono mb-4">
          Platform
        </h2>
        <div className="space-y-3">
          {[
            { label: 'Backend API', href: 'http://localhost:8000/health', status: 'check /health' },
            { label: 'Vector Store', status: 'Qdrant :6333' },
            { label: 'AI Engine', status: 'coming soon' },
          ].map(({ label, status }) => (
            <div key={label} className="flex items-center justify-between">
              <span className="text-stone-300 text-[13px]">{label}</span>
              <span className="font-mono text-stone-600 text-[11px]">{status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
