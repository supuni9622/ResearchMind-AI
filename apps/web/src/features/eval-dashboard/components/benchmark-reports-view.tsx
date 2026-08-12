'use client';

import { useEffect, useState } from 'react';
import { api, type BenchmarkReportResult } from '@/lib/api';
import { EmptyState } from '@/components/ui/empty-state';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function formatMetric(value: number | string | boolean): string {
  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  }
  return String(value);
}

export function BenchmarkReportCard({ report }: { report: BenchmarkReportResult }) {
  const metricKeys = Array.from(
    new Set(report.candidates.flatMap((candidate) => Object.keys(candidate.metrics)))
  );

  return (
    <div className="border border-ink-700 rounded-xl p-5 mb-5">
      <div className="flex items-baseline justify-between mb-1 gap-4">
        <p className="font-display text-amber-400 text-[15px] font-mono truncate">
          {report.benchmark_name}
        </p>
        <span className="font-mono text-stone-600 text-[11px] whitespace-nowrap">
          {formatDate(report.generated_at)}
        </span>
      </div>
      <p className="text-stone-600 text-[12px] mb-4">
        {report.dataset.name} · {report.dataset.document_count} docs
        {report.metadata.branch ? ` · ${report.metadata.branch}` : ''}
        {report.metadata.git_commit ? ` @ ${report.metadata.git_commit.slice(0, 7)}` : ''}
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-ink-700">
              <th className="text-left font-mono text-stone-600 text-[10px] tracking-widest uppercase py-2 pr-4">
                Candidate
              </th>
              {metricKeys.map((key) => (
                <th
                  key={key}
                  className="text-right font-mono text-stone-600 text-[10px] tracking-widest uppercase py-2 pl-4 whitespace-nowrap"
                >
                  {key}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {report.candidates.map((candidate) => (
              <tr key={candidate.name} className="border-b border-ink-800 last:border-0">
                <td className="py-2 pr-4 text-stone-200 whitespace-nowrap">
                  {candidate.name}
                  {candidate.version && (
                    <span className="text-stone-600 text-[11px] ml-1.5">{candidate.version}</span>
                  )}
                </td>
                {metricKeys.map((key) => (
                  <td
                    key={key}
                    className="py-2 pl-4 text-right font-mono text-stone-300 whitespace-nowrap"
                  >
                    {key in candidate.metrics ? (
                      formatMetric(candidate.metrics[key])
                    ) : (
                      <span className="text-stone-700">—</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function BenchmarkReportsView({ onForbidden }: { onForbidden: () => void }) {
  const [reports, setReports] = useState<BenchmarkReportResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const res = await api.evalDashboard.listBenchmarkReports();
        if (!cancelled) setReports(res);
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
  }, [onForbidden]);

  if (loading) {
    return (
      <div className="text-center py-16 border border-dashed border-ink-600 rounded-xl">
        <p className="text-stone-600 text-sm">Loading…</p>
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <EmptyState
        title="No benchmark reports on disk"
        description="Run one with `python -m benchmarks.runner <name> --dataset ...` to produce a report.json here."
      />
    );
  }

  return (
    <div>
      <p className="text-stone-600 text-[12px] mb-5">
        Latest local run of each engineering benchmark — read straight off disk, no history beyond
        what&apos;s there right now. GoldenSetGeneration/ProductionFailuresRegression aren&apos;t
        listed here — see their aggregate metrics at the top of the Offline Benchmark tab instead.
      </p>
      {reports.map((report) => (
        <BenchmarkReportCard key={report.benchmark_name} report={report} />
      ))}
    </div>
  );
}
