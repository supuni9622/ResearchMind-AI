import type { Document } from '@/lib/api';

const TAG_POOL = ['methodology', 'survey', 'benchmark', 'dataset', 'theory', 'case-study'];

function hashSeed(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return h;
}

export interface DocumentMeta {
  pageCount: number;
  chunkCount: number;
  embeddingCount: number;
  tags: string[];
}

export function getDocumentMeta(doc: Document): DocumentMeta {
  const seed = hashSeed(doc.id || doc.filename);
  const pageCount = 4 + (seed % 40);
  const chunkCount = pageCount * (2 + (seed % 3));
  const tags = [TAG_POOL[seed % TAG_POOL.length], TAG_POOL[(seed >> 3) % TAG_POOL.length]].filter(
    (t, i, arr) => arr.indexOf(t) === i
  );

  return {
    pageCount,
    chunkCount,
    embeddingCount: chunkCount,
    tags,
  };
}

export type DocKind = 'pdf' | 'docx' | 'markdown' | 'other';

export function getDocKind(doc: Document): DocKind {
  const ct = doc.content_type.toLowerCase();
  const name = doc.filename.toLowerCase();
  if (ct.includes('pdf') || name.endsWith('.pdf')) return 'pdf';
  if (ct.includes('word') || name.endsWith('.docx') || name.endsWith('.doc')) return 'docx';
  if (ct.includes('markdown') || name.endsWith('.md')) return 'markdown';
  return 'other';
}

export const DOC_KIND_LABEL: Record<DocKind, string> = {
  pdf: 'PDF',
  docx: 'DOCX',
  markdown: 'Markdown',
  other: 'Other',
};
