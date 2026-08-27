'use client';

import { useEffect, useState } from 'react';
import {
  api,
  type ContentSegmentAggregate,
  type ContentSegmentField,
  type FingerprintField,
  type FingerprintSegmentAggregate,
} from '@/lib/api';
import { EmptyState } from '@/components/ui/empty-state';

const FINGERPRINT_FIELDS: FingerprintField[] = [
  'prompt_version',
  'surface',
  'chunking_strategy',
  'embedding_model',
  'reranker',
  'routing_strategy',
];

const CONTENT_SEGMENT_FIELDS: ContentSegmentField[] = [
  'query_type',
  'difficulty',
  'workflow',
  'failure_category',
];

const EXAMPLE_METRIC_NAMES = [
  'faithfulness',
  'answer_relevancy',
  'citation_validity',
  'rubric_adherence',
  'web_search_invoked',
  'web_search_success',
  'paper_search_invoked',
  'paper_search_success',
];
/**
 * `metric_name` is free text, not a closed enum (new metrics like E23's
 * tool-invocation ones need no dashboard change to become queryable) --
 * these are just a discoverability aid so a user doesn't need to already
 * know a metric name exists to find it. web_search_invoked/success and
 * paper_search_invoked/success are Chat-only (E23,
 * `EVALUATION_PLAN.md` §10): Linear Research has no web/paper search
 * wiring, and Deep Research's search happens outside any single
 * generation's `eval_scores` row, so slicing them by `surface` will only
 * ever show `chat`.
 */

function formatNumber(value: number | null): string {
  return value === null ? '—' : value.toFixed(3);
}

function AggregateTable({
  rows,
  valueLabel,
}: {
  rows: { value: string | null; count: number; avgScore: number | null; passRate: number | null }[];
  valueLabel: string;
}) {
  if (rows.length === 0) {
    return (
      <div className="text-center py-10 border border-dashed border-ink-600 rounded-xl">
        <p className="text-stone-600 text-[13px]">No scores for this metric yet.</p>
      </div>
    );
  }

  return (
    <table className="w-full text-[13px]">
      <thead>
        <tr className="border-b border-ink-700">
          <th className="text-left font-mono text-stone-600 text-[10px] tracking-widest uppercase py-2 pr-4">
            {valueLabel}
          </th>
          <th className="text-right font-mono text-stone-600 text-[10px] tracking-widest uppercase py-2 pl-4">
            Count
          </th>
          <th className="text-right font-mono text-stone-600 text-[10px] tracking-widest uppercase py-2 pl-4">
            Avg Score
          </th>
          <th className="text-right font-mono text-stone-600 text-[10px] tracking-widest uppercase py-2 pl-4">
            Pass Rate
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.value ?? '—'} className="border-b border-ink-800 last:border-0">
            <td className="py-2 pr-4 text-stone-200 font-mono">{row.value ?? '(null)'}</td>
            <td className="py-2 pl-4 text-right text-stone-300 font-mono">{row.count}</td>
            <td className="py-2 pl-4 text-right text-stone-300 font-mono">
              {formatNumber(row.avgScore)}
            </td>
            <td className="py-2 pl-4 text-right text-stone-300 font-mono">
              {formatNumber(row.passRate)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function FieldSelect<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: T[];
  onChange: (value: T) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as T)}
      className="px-3 py-1.5 rounded-lg bg-ink-800 border border-ink-600 text-stone-200 text-[13px] focus:outline-none focus:border-sage-600"
    >
      {options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}

export function SegmentAnalysisView({ onForbidden }: { onForbidden: () => void }) {
  const [metricName, setMetricName] = useState('faithfulness');
  const [fingerprintField, setFingerprintField] = useState<FingerprintField>('prompt_version');
  const [segmentField, setSegmentField] = useState<ContentSegmentField>('query_type');

  const [onlineRows, setOnlineRows] = useState<FingerprintSegmentAggregate[]>([]);
  const [offlineRows, setOfflineRows] = useState<ContentSegmentAggregate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      setLoading(true);
      try {
        const [online, offline] = await Promise.all([
          api.evalDashboard.segmentAnalysisOnline({ metricName, fingerprintField }),
          api.evalDashboard.segmentAnalysisOffline({ metricName, segmentField }),
        ]);
        if (cancelled) return;
        setOnlineRows(online.items);
        setOfflineRows(offline.items);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof Error && (err as Error & { status?: number }).status === 403) {
          onForbidden();
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [metricName, fingerprintField, segmentField, onForbidden]);

  return (
    <div>
      <p className="text-stone-600 text-[12px] mb-5">
        Two dimensions, because that&apos;s genuinely what the data supports — online-sampled rows
        can be sliced by a config-fingerprint field (e.g. did <code>prompt_version</code> &quot;chat-v1&quot;
        vs &quot;chat-v2&quot; change this metric), since only those rows have a linked generation to pull a
        fingerprint from. Offline golden-set rows have no fingerprint, but do resolve to a
        <code> query_type</code>/<code>difficulty</code>/<code>workflow</code> instead. No automated
        before/after diffing — read the rows and compare by eye, same as the rest of this dashboard.
      </p>

      <div className="flex items-center gap-3 mb-3">
        <label className="text-stone-500 text-[12px] font-mono">metric_name</label>
        <input
          type="text"
          value={metricName}
          onChange={(e) => setMetricName(e.target.value)}
          placeholder="faithfulness"
          className="px-3 py-1.5 rounded-lg bg-ink-800 border border-ink-600 text-stone-200 text-[13px] font-mono placeholder:text-stone-600 focus:outline-none focus:border-sage-600 w-56"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-6">
        {EXAMPLE_METRIC_NAMES.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => setMetricName(name)}
            className={`px-2 py-1 rounded-md text-[11px] font-mono border transition-colors ${
              metricName === name
                ? 'border-sage-600 text-sage-400 bg-sage-800/40'
                : 'border-ink-700 text-stone-500 hover:text-stone-300 hover:border-ink-600'
            }`}
          >
            {name}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="border border-ink-700 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="font-display text-amber-400 text-[15px] font-mono">
              By Config Fingerprint (Online)
            </p>
            <FieldSelect
              value={fingerprintField}
              options={FINGERPRINT_FIELDS}
              onChange={setFingerprintField}
            />
          </div>
          {loading ? (
            <p className="text-stone-600 text-[13px] py-4">Loading…</p>
          ) : (
            <AggregateTable
              valueLabel={fingerprintField}
              rows={onlineRows.map((row) => ({
                value: row.fingerprint_value,
                count: row.count,
                avgScore: row.avg_score,
                passRate: row.pass_rate,
              }))}
            />
          )}
        </div>

        <div className="border border-ink-700 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="font-display text-amber-400 text-[15px] font-mono">
              By Content Segment (Offline)
            </p>
            <FieldSelect
              value={segmentField}
              options={CONTENT_SEGMENT_FIELDS}
              onChange={setSegmentField}
            />
          </div>
          {loading ? (
            <p className="text-stone-600 text-[13px] py-4">Loading…</p>
          ) : (
            <AggregateTable
              valueLabel={segmentField}
              rows={offlineRows.map((row) => ({
                value: row.segment_value,
                count: row.count,
                avgScore: row.avg_score,
                passRate: row.pass_rate,
              }))}
            />
          )}
        </div>
      </div>

      {!loading && onlineRows.length === 0 && offlineRows.length === 0 && (
        <div className="mt-6">
          <EmptyState
            title={`No "${metricName}" scores found`}
            description="Check the metric name — common ones are faithfulness, answer_relevancy, context_precision, context_recall, citation_validity, user_rating."
          />
        </div>
      )}
    </div>
  );
}
