'use client';

import { motion } from 'framer-motion';
import { STREAM_STAGES, type StreamStage } from '@/features/research/types';
import { CheckCircleIcon } from '@/components/ui/icons';

export function StreamingStatus({ currentStage }: { currentStage: StreamStage }) {
  const currentIndex = STREAM_STAGES.indexOf(currentStage);

  return (
    <div className="max-w-2xl border border-ink-600 rounded-xl p-4">
      <div className="space-y-2">
        {STREAM_STAGES.map((stage, i) => {
          const done = i < currentIndex;
          const active = i === currentIndex;
          if (i > currentIndex) return null;
          return (
            <motion.div
              key={stage}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className="flex items-center gap-2.5"
            >
              {done ? (
                <span className="text-sage-500 flex-shrink-0">
                  <CheckCircleIcon size={13} />
                </span>
              ) : (
                <span className="w-3 h-3 flex-shrink-0 flex items-center justify-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-sage-500 animate-pulse" />
                </span>
              )}
              <span className={`text-[13px] ${active ? 'text-stone-200' : 'text-stone-600'}`}>
                {stage}
              </span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
