'use client';

import { motion } from 'framer-motion';
import { LoginButton } from '@/components/auth/login-button';

const STRIP = [
  { label: 'Upload', sub: 'PDF · DOCX · TXT' },
  { label: 'Query', sub: 'Natural language' },
  { label: 'Cite', sub: 'Source-grounded' },
  { label: 'Synthesize', sub: 'Cross-document' },
  { label: 'Deep Research', sub: 'Multi-step reasoning' },
];

export function Hero() {
  return (
    <>
      <section className="flex-1 flex flex-col items-center justify-center px-6 pt-24 pb-20 text-center">
        <motion.div
          className="max-w-3xl mx-auto"
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
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
            Upload your documents. Ask precise questions. Get answers grounded
            in your sources, with citations you can verify.
          </p>

          <LoginButton variant="primary" />
        </motion.div>
      </section>

      <section className="border-t border-ink-600/60 px-8 py-5">
        <motion.div
          className="max-w-4xl mx-auto flex flex-wrap items-center justify-center gap-x-10 gap-y-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.25 }}
        >
          {STRIP.map(({ label, sub }) => (
            <div key={label} className="flex items-center gap-2">
              <span className="text-stone-200 text-sm font-medium">{label}</span>
              <span className="text-ink-500">·</span>
              <span className="font-mono text-stone-500 text-[11px]">{sub}</span>
            </div>
          ))}
        </motion.div>
      </section>
    </>
  );
}
