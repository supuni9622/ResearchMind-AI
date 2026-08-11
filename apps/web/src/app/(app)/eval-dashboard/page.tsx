'use client';

import { useState } from 'react';
import { PageHeader } from '@/components/ui/page-header';
import { EmptyState } from '@/components/ui/empty-state';
import { Pill } from '@/components/ui/badge';
import { OwnerDrilldownView } from '@/features/eval-dashboard/components/owner-drilldown-view';
import { OfflineDrilldownView } from '@/features/eval-dashboard/components/offline-drilldown-view';
import { BenchmarkReportsView } from '@/features/eval-dashboard/components/benchmark-reports-view';

type Tab = 'owner' | 'offline' | 'benchmarks';

export default function EvalDashboardPage() {
  const [forbidden, setForbidden] = useState(false);
  const [tab, setTab] = useState<Tab>('owner');

  if (forbidden) {
    return (
      <div className="px-8 py-10 max-w-2xl">
        <PageHeader eyebrow="Internal" title="Eval Dashboard" />
        <EmptyState
          title="You don't have access to this page"
          description="This is an internal tool, limited to a configured allowlist of engineer emails."
        />
      </div>
    );
  }

  return (
    <div className="px-8 py-10 max-w-6xl">
      <PageHeader eyebrow="Internal" title="Eval Dashboard" />
      <p className="text-stone-500 text-[13px] -mt-5 mb-6">
        View over `eval_scores` — online-sampled automated scores, human feedback, and offline
        benchmark results. Offline rows have no owner, so they get their own tab rather than a
        (broken) filter on the owner-scoped view.
      </p>

      <div className="flex items-center gap-2 mb-6">
        <Pill active={tab === 'owner'} onClick={() => setTab('owner')}>
          By Owner
        </Pill>
        <Pill active={tab === 'offline'} onClick={() => setTab('offline')}>
          Offline Benchmark
        </Pill>
        <Pill active={tab === 'benchmarks'} onClick={() => setTab('benchmarks')}>
          Engineering Benchmarks
        </Pill>
      </div>

      {tab === 'owner' && <OwnerDrilldownView onForbidden={() => setForbidden(true)} />}
      {tab === 'offline' && <OfflineDrilldownView onForbidden={() => setForbidden(true)} />}
      {tab === 'benchmarks' && <BenchmarkReportsView onForbidden={() => setForbidden(true)} />}
    </div>
  );
}
