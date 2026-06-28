'use client';

import { useEffect, useRef, useState } from 'react';

interface Source {
  id: number;
  filename: string;
  excerpt: string;
  page?: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
}

// Placeholder until the AI engine is wired up
async function mockAnswer(
  question: string
): Promise<{ content: string; sources: Source[] }> {
  await new Promise((r) => setTimeout(r, 1100));
  return {
    content: `This is where your AI-generated answer to "${question}" will appear — grounded in your uploaded documents with inline citations [¹] for each claim drawn from a specific source. Connect the AI engine to replace this placeholder.`,
    sources: [
      {
        id: 1,
        filename: 'example-paper.pdf',
        excerpt:
          'A relevant excerpt from the source document that supports the claim above would appear here.',
        page: 4,
      },
    ],
  };
}

function LogoIcon() {
  return (
    <div className="w-5 h-5 rounded bg-sage-700 flex items-center justify-center flex-shrink-0">
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
        <path
          d="M1 1h3.5v3.5H1zM5.5 1H9v3.5H5.5zM1 5.5h3.5V9H1zM7.25 5.5a1.75 1.75 0 1 1 0 3.5 1.75 1.75 0 0 1 0-3.5z"
          fill="white"
        />
      </svg>
    </div>
  );
}

function UserMessage({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-lg bg-ink-700 border border-ink-500 rounded-2xl rounded-tr-sm px-4 py-3">
        <p className="text-stone-200 text-sm leading-relaxed">{content}</p>
      </div>
    </div>
  );
}

function AssistantMessage({ content, sources }: { content: string; sources?: Source[] }) {
  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-2 mb-3">
        <LogoIcon />
        <span className="font-mono text-stone-600 text-[11px]">ResearchMind</span>
      </div>

      <p className="text-stone-200 text-sm leading-relaxed mb-4">{content}</p>

      {sources && sources.length > 0 && (
        <div className="border border-ink-600 rounded-lg overflow-hidden">
          <div className="px-4 py-2.5 bg-ink-800 border-b border-ink-700 flex items-center gap-2">
            <span
              className="font-display text-amber-400"
              style={{
                fontSize: '0.8125rem',
                fontVariationSettings: "'opsz' 20, 'SOFT' 0",
              }}
            >
              Sources
            </span>
            <span className="font-mono text-stone-600 text-[10px]">{sources.length}</span>
          </div>
          <div className="divide-y divide-ink-700">
            {sources.map((src) => (
              <div key={src.id} className="px-4 py-3 flex gap-3">
                <span className="font-mono text-amber-500 text-[11px] flex-shrink-0 mt-0.5">
                  [{src.id}]
                </span>
                <div className="min-w-0">
                  <p className="font-mono text-stone-300 text-[11px] font-medium mb-1">
                    {src.filename}
                    {src.page != null && (
                      <span className="text-stone-600"> · p. {src.page}</span>
                    )}
                  </p>
                  <p className="text-stone-500 text-[12px] leading-relaxed line-clamp-2">
                    {src.excerpt}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2.5">
      <LogoIcon />
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-stone-700 animate-bounce"
            style={{ animationDelay: `${i * 0.14}s` }}
          />
        ))}
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  'What are the key findings across my documents?',
  'Summarize the main arguments in my sources',
  'What methodology was used in the research?',
];

function EmptyState({ onSuggest }: { onSuggest: (q: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full max-w-sm mx-auto text-center">
      <div className="w-12 h-12 rounded-xl bg-ink-800 border border-ink-600 flex items-center justify-center mb-4">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="9" cy="9" r="7" stroke="#252D3A" strokeWidth="1.5" />
          <circle cx="9" cy="9" r="7" stroke="#6B6560" strokeWidth="1.5" />
          <path d="M14.5 14.5l4 4" stroke="#6B6560" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </div>
      <h2 className="text-stone-300 text-sm font-medium mb-2">Start a research session</h2>
      <p className="text-stone-500 text-[13px] mb-8 leading-relaxed">
        Ask a question and ResearchMind will search your documents and return a cited answer.
      </p>
      <div className="w-full space-y-2">
        {SUGGESTIONS.map((s) => (
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

export default function ResearchPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const { content, sources } = await mockAnswer(question);
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'assistant', content, sources },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'Something went wrong. Please try again.',
        },
      ]);
    } finally {
      setLoading(false);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  }

  return (
    <div className="flex flex-col h-screen">
      <div className="px-8 pt-8 pb-4 border-b border-ink-600 flex-shrink-0">
        <p className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase mb-1">
          AI Research
        </p>
        <h1
          className="font-display text-stone-100"
          style={{
            fontSize: '1.875rem',
            fontVariationSettings: "'opsz' 40, 'SOFT' 0, 'WONK' 0",
          }}
        >
          Research
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto px-8 py-6 scrollbar-thin">
        {messages.length === 0 && !loading ? (
          <EmptyState onSuggest={setInput} />
        ) : (
          <div className="max-w-2xl space-y-8">
            {messages.map((msg) =>
              msg.role === 'user' ? (
                <UserMessage key={msg.id} content={msg.content} />
              ) : (
                <AssistantMessage
                  key={msg.id}
                  content={msg.content}
                  sources={msg.sources}
                />
              )
            )}
            {loading && <ThinkingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="flex-shrink-0 border-t border-ink-600 px-8 py-5 bg-ink-950/80 backdrop-blur-sm">
        <form onSubmit={handleSubmit} className="max-w-2xl">
          <div className="flex gap-2.5 items-end">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a research question…"
                rows={1}
                disabled={loading}
                className="w-full bg-ink-800 border border-ink-500 rounded-xl px-4 py-2.5 text-stone-100 text-sm placeholder-stone-600 resize-none focus:outline-none focus:border-sage-600 transition-colors min-h-[42px] max-h-36 overflow-y-auto scrollbar-thin"
                style={{ fieldSizing: 'content' } as React.CSSProperties}
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="flex-shrink-0 w-9 h-9 rounded-xl bg-sage-600 hover:bg-sage-500 disabled:bg-ink-700 disabled:text-stone-700 text-stone-100 flex items-center justify-center transition-colors duration-150"
            >
              {loading ? (
                <div className="w-3.5 h-3.5 border border-current/30 border-t-current rounded-full animate-spin" />
              ) : (
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                  <path
                    d="M2 7h10M8 3l4 4-4 4"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
            </button>
          </div>
          <p className="mt-1.5 font-mono text-stone-700 text-[10px]">
            Enter to send · Shift + Enter for new line
          </p>
        </form>
      </div>
    </div>
  );
}
