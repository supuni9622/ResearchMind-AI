import Link from 'next/link';
import { SearchIcon, SparklesIcon } from '@/components/ui/icons';
import type { ResearchMode } from '@/features/research/types';

const LINEAR_SUGGESTIONS = [
  'What are the key findings across my documents?',
  'Summarize the main arguments in my sources',
  'What methodology was used in the research?',
];

const LINEAR_SUGGESTIONS_NO_DOCS = [
  'Explain a core concept in this field',
  'What background would I need before reading a paper on this topic?',
  'What are the standard methodologies used in this area?',
];

const DEEP_SUGGESTIONS = [
  'Write a literature review on this topic, drawing on my documents and the web',
  'Produce a research report comparing the methodologies across my sources',
  'Synthesize a draft article, flagging where the evidence is thin',
];

export function EmptyWorkspace({
  mode,
  hasDocuments,
  onSuggest,
}: {
  mode: ResearchMode;
  /** `null` while the document count is still loading -- treated the same as `true` so the copy doesn't flash a "no documents" warning before the check resolves. */
  hasDocuments: boolean | null;
  onSuggest: (q: string) => void;
}) {
  const deep = mode === 'deep';
  const emptyLibrary = !deep && hasDocuments === false;
  const suggestions = deep
    ? DEEP_SUGGESTIONS
    : emptyLibrary
      ? LINEAR_SUGGESTIONS_NO_DOCS
      : LINEAR_SUGGESTIONS;

  return (
    <div className="flex flex-col items-center justify-center h-full max-w-sm mx-auto text-center">
      <div className="w-12 h-12 rounded-xl bg-ink-800 border border-ink-600 flex items-center justify-center mb-4 text-stone-600">
        {deep ? <SparklesIcon size={18} /> : <SearchIcon size={18} />}
      </div>
      <h2 className="text-stone-300 text-sm font-medium mb-2">
        {deep ? 'Start a deep research run' : 'Start a research session'}
      </h2>
      <p className="text-stone-500 text-[13px] mb-8 leading-relaxed">
        {deep ? (
          "Describe the report you want. You'll review the plan, then the final draft, before anything is published — with web and paper search available along the way."
        ) : emptyLibrary ? (
          <>
            Your library is empty, so answers here will be generated from general knowledge and
            clearly flagged as such.{' '}
            <Link href="/documents" className="text-sage-500 hover:text-sage-400 transition-colors">
              Upload documents
            </Link>{' '}
            first for grounded, cited answers.
          </>
        ) : (
          'Ask a question and ResearchMind will search your documents and return a cited answer.'
        )}
      </p>
      <div className="w-full space-y-2">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => onSuggest(s)}
            className="w-full text-left px-4 py-3 border border-ink-600 rounded-lg text-stone-400 text-[13px] hover:border-ink-400 hover:text-stone-200 hover:bg-ink-800/50 transition-all duration-100"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
