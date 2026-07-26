'use client';

import { motion } from 'framer-motion';
import { MessageIcon, FileTextIcon, NetworkIcon, CheckCircleIcon, ArrowDownIcon } from '@/components/ui/icons';

const STAGES = [
  {
    icon: MessageIcon,
    title: 'Chat',
    description: 'Brainstorm your question and find papers worth reading, web and paper search included.',
  },
  {
    icon: FileTextIcon,
    title: 'Documents',
    description: 'Download what matters and upload it — PDFs, DOCX, and Markdown, chunked and indexed.',
  },
  {
    icon: NetworkIcon,
    title: 'Research Runtime',
    description: 'Linear Research answers fast and cited; Deep Research plans, gathers, and drafts with your approval at each step.',
  },
  {
    icon: CheckCircleIcon,
    title: 'Grounded Draft',
    description: 'A cited, verifiable answer or report — traceable to the originating passage, with related papers suggested.',
  },
];

export function ArchitectureSection() {
  return (
    <section className="border-t border-ink-600/60 px-8 py-20 bg-ink-900/30">
      <div className="max-w-md mx-auto">
        <motion.div
          className="mb-12 text-center"
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.5 }}
        >
          <p className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase mb-2">
            How it works
          </p>
          <h2
            className="font-display text-stone-100"
            style={{ fontSize: '1.75rem', fontVariationSettings: "'opsz' 40, 'SOFT' 0" }}
          >
            From open brainstorming to a grounded draft.
          </h2>
        </motion.div>

        <div className="flex flex-col items-stretch">
          {STAGES.map(({ icon: Icon, title, description }, i) => (
            <div key={title} className="flex flex-col items-center">
              <motion.div
                className="w-full border border-ink-600 rounded-xl p-5 bg-ink-950/60 flex items-start gap-4"
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-60px' }}
                transition={{ duration: 0.45, delay: i * 0.08 }}
              >
                <div className="w-9 h-9 rounded-lg bg-ink-800 border border-ink-600 flex items-center justify-center flex-shrink-0 text-sage-400">
                  <Icon size={16} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-stone-700 text-[10px]">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <h3 className="text-stone-100 text-sm font-medium">{title}</h3>
                  </div>
                  <p className="text-stone-500 text-[13px] leading-relaxed">{description}</p>
                </div>
              </motion.div>

              {i < STAGES.length - 1 && (
                <div className="text-ink-500 py-2">
                  <ArrowDownIcon size={14} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
