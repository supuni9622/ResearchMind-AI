'use client';

import { motion } from 'framer-motion';
import type { ResearchStage } from '@/features/research/types';
import { CheckCircleIcon } from '@/components/ui/icons';

export function StreamingStatus({
  stage,
  chunkCount,
}: {
  stage: ResearchStage;
  chunkCount?: number;
}) {
  const searchDone = stage === 'generating' || stage === 'done';

  return (
    <div className="max-w-2xl border border-ink-600 rounded-xl p-4">
      <div className="space-y-2">
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="flex items-center gap-2.5"
        >
          {searchDone ? (
            <span className="text-sage-500 flex-shrink-0">
              <CheckCircleIcon size={13} />
            </span>
          ) : (
            <span className="w-3 h-3 flex-shrink-0 flex items-center justify-center">
              <span className="w-1.5 h-1.5 rounded-full bg-sage-500 animate-pulse" />
            </span>
          )}
          <span className={`text-[13px] ${searchDone ? 'text-stone-600' : 'text-stone-200'}`}>
            {searchDone
              ? `Found ${chunkCount ?? 0} relevant passage${chunkCount === 1 ? '' : 's'}`
              : 'Searching your documents…'}
          </span>
        </motion.div>

        {stage === 'generating' && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            className="flex items-center gap-2.5"
          >
            <span className="w-3 h-3 flex-shrink-0 flex items-center justify-center">
              <span className="w-1.5 h-1.5 rounded-full bg-sage-500 animate-pulse" />
            </span>
            <span className="text-stone-200 text-[13px]">Generating answer…</span>
          </motion.div>
        )}
      </div>
    </div>
  );
}
