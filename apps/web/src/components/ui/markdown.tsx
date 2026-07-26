'use client';

import type { Root, Text } from 'mdast';
import type { ReactNode } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';
import type { Pluggable } from 'unified';
import type { Citation } from '@/lib/api';
import { isWebCitation } from '@/features/research/types';
import { NetworkIcon } from '@/components/ui/icons';

// Matches both document citations (`S1`) and web citations (`W1-1`) --
// identical token this app's answers have always used (see
// `research-block.tsx`'s previous `renderAnswer`).
const CITATION_TOKEN = /\[?(S\d+|W\d+-\d+)\]?/g;

/** A remark plugin (factory, since it needs this render's known citation
 * ids) that splits citation tokens out of text nodes into their own
 * `citation` mdast nodes, tagged via `data.hName`/`hProperties` so
 * `react-markdown` can render them through a normal `components` entry --
 * this keeps citation badges working *inside* properly parsed markdown
 * (a paragraph split by a citation is still one paragraph), rather than
 * pre-splitting the raw string and losing block structure. An id not in
 * `knownIds` is left as plain text, exactly like the function this
 * replaces. */
function remarkCitations(knownIds: Set<string>) {
  return function transformer(tree: Root) {
    visitTextNodes(tree, (node, index, parent) => {
      const value = node.value;
      CITATION_TOKEN.lastIndex = 0;
      if (!CITATION_TOKEN.test(value)) return;

      const replacement: (Text | { type: 'citation'; data: Record<string, unknown> })[] = [];
      let lastIndex = 0;
      let match: RegExpExecArray | null;
      CITATION_TOKEN.lastIndex = 0;
      while ((match = CITATION_TOKEN.exec(value)) !== null) {
        const id = match[1];
        if (!knownIds.has(id)) continue;
        if (match.index > lastIndex) {
          replacement.push({ type: 'text', value: value.slice(lastIndex, match.index) });
        }
        replacement.push({
          type: 'citation',
          data: { hName: 'citation', hProperties: { id } },
        });
        lastIndex = match.index + match[0].length;
      }
      if (replacement.length === 0) return;
      if (lastIndex < value.length) {
        replacement.push({ type: 'text', value: value.slice(lastIndex) });
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      parent.children.splice(index, 1, ...(replacement as any[]));
    });
  };
}

/** Minimal manual mdast walk (no `unist-util-visit` dependency) -- visits
 * every `text` node, letting the callback splice its parent's children in
 * place. Walks a snapshot of each level so in-place splices don't disturb
 * the traversal. */
function visitTextNodes(
  node: { type: string; children?: unknown[] },
  callback: (node: Text, index: number, parent: { children: unknown[] }) => void
): void {
  if (!node.children) return;
  for (const child of [...node.children] as { type: string; children?: unknown[] }[]) {
    if (child.type === 'text') {
      const index = node.children.indexOf(child);
      if (index !== -1) {
        callback(child as Text, index, node as { children: unknown[] });
      }
      continue;
    }
    visitTextNodes(child, callback);
  }
}

function CitationBadge({ id }: { id: string }) {
  const web = isWebCitation(id);
  return (
    <span
      title={web ? 'Found via web search' : undefined}
      className={`inline-flex items-center gap-0.5 font-mono text-[0.82em] px-1 py-0.5 rounded border whitespace-nowrap ${
        web
          ? 'text-sky-400 border-sky-800/40 bg-sky-500/5'
          : 'text-amber-500 border-amber-800/40 bg-amber-500/5'
      }`}
    >
      {web && <NetworkIcon size={9} />}
      [{id.slice(1)}]
    </span>
  );
}

const BASE_COMPONENTS: Components = {
  p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
  h1: ({ children }) => (
    <h1 className="font-display text-stone-100 text-lg mt-5 mb-2 first:mt-0">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="font-display text-stone-100 text-base mt-4 mb-2 first:mt-0">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-stone-100 text-sm font-semibold mt-4 mb-1.5 first:mt-0">{children}</h3>
  ),
  h4: ({ children }) => (
    <h4 className="text-stone-200 text-sm font-semibold mt-3 mb-1.5 first:mt-0">{children}</h4>
  ),
  ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1 last:mb-0">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1 last:mb-0">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => <strong className="text-stone-100 font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-sage-400 hover:text-sage-300 underline underline-offset-2 transition-colors"
    >
      {children}
    </a>
  ),
  code: ({ children, className }) => {
    const isBlock = Boolean(className);
    return isBlock ? (
      <code className={`${className ?? ''} font-mono text-[0.85em]`}>{children}</code>
    ) : (
      <code className="font-mono text-[0.85em] px-1 py-0.5 rounded bg-ink-800 border border-ink-600 text-sage-300">
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="mb-3 last:mb-0 p-3 rounded-lg bg-ink-800 border border-ink-600 overflow-x-auto">
      {children}
    </pre>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-ink-500 pl-3 mb-3 last:mb-0 text-stone-400 italic">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="border-ink-600 my-4" />,
  table: ({ children }) => (
    <div className="mb-3 last:mb-0 overflow-x-auto">
      <table className="min-w-full text-left border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="border-b border-ink-600">{children}</thead>,
  th: ({ children }) => (
    <th className="px-2 py-1.5 font-mono text-[10px] uppercase tracking-wider text-stone-500">
      {children}
    </th>
  ),
  td: ({ children }) => <td className="px-2 py-1.5 border-t border-ink-700">{children}</td>,
  // @ts-expect-error -- `citation` is a custom node type introduced by
  // `remarkCitations`, not part of react-markdown's built-in element map.
  citation: ({ id }: { id: string }) => <CitationBadge id={id} />,
};

export function Markdown({
  content,
  citations,
  className,
}: {
  content: string;
  citations?: Citation[];
  className?: string;
}): ReactNode {
  const knownIds = new Set((citations ?? []).map((c) => c.citation_id));
  const remarkPlugins: Pluggable[] = [
    remarkGfm,
    remarkBreaks,
    ...(knownIds.size > 0 ? [[remarkCitations, knownIds] as Pluggable] : []),
  ];

  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={remarkPlugins} components={BASE_COMPONENTS}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
