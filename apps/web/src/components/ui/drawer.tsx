'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { CloseIcon } from './icons';

export function Drawer({
  open,
  onClose,
  title,
  eyebrow,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  eyebrow?: string;
  children: React.ReactNode;
}) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 bg-black/40 z-40"
            onClick={onClose}
          />
          <motion.aside
            key="panel"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="fixed top-0 right-0 h-screen w-full max-w-md bg-ink-900 border-l border-ink-600 z-50 flex flex-col"
          >
            <div className="flex items-start justify-between px-6 py-5 border-b border-ink-600 flex-shrink-0">
              <div>
                {eyebrow && (
                  <p className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase mb-1.5">
                    {eyebrow}
                  </p>
                )}
                <h2 className="text-stone-100 text-base font-medium">{title}</h2>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 text-stone-600 hover:text-stone-300 rounded transition-colors flex-shrink-0"
                aria-label="Close"
              >
                <CloseIcon />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto scrollbar-thin px-6 py-5">{children}</div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
