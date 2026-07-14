'use client';

import { motion } from 'framer-motion';
import {
  UploadIcon,
  SearchIcon,
  TagIcon,
  LayersIcon,
  NetworkIcon,
} from '@/components/ui/icons';

const FEATURES = [
  {
    icon: UploadIcon,
    title: 'Upload',
    description:
      'Bring PDFs, Word documents, and Markdown into a single research library — no folder structure required.',
  },
  {
    icon: SearchIcon,
    title: 'Query',
    description:
      'Ask in plain language. ResearchMind retrieves the exact passages that matter, across every document you own.',
  },
  {
    icon: TagIcon,
    title: 'Cite',
    description:
      'Every claim traces back to a source, a page, and a passage — verify anything with one click.',
  },
  {
    icon: LayersIcon,
    title: 'Synthesize',
    description:
      'Cross-document reasoning surfaces patterns and contradictions a single-file search would miss.',
  },
  {
    icon: NetworkIcon,
    title: 'Deep Research',
    description:
      'Multi-step research sessions — planning, retrieval, and review — for questions that take more than one pass.',
  },
];

export function FeaturesSection() {
  return (
    <section className="border-t border-ink-600/60 px-8 py-20">
      <div className="max-w-5xl mx-auto">
        <motion.div
          className="mb-12 max-w-md"
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.5 }}
        >
          <p className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase mb-2">
            Capabilities
          </p>
          <h2
            className="font-display text-stone-100"
            style={{ fontSize: '1.75rem', fontVariationSettings: "'opsz' 40, 'SOFT' 0" }}
          >
            One workspace, every step of research.
          </h2>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {FEATURES.map(({ icon: Icon, title, description }, i) => (
            <motion.div
              key={title}
              className="border border-ink-600 rounded-xl p-5 hover:border-ink-400 transition-colors duration-150"
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.45, delay: i * 0.06 }}
            >
              <div className="w-8 h-8 rounded-lg bg-ink-800 border border-ink-600 flex items-center justify-center mb-4 text-sage-400">
                <Icon size={15} />
              </div>
              <h3 className="text-stone-100 text-sm font-medium mb-1.5">{title}</h3>
              <p className="text-stone-500 text-[13px] leading-relaxed">{description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
