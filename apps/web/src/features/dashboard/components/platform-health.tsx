'use client';

import { useEffect, useState } from 'react';
import { SectionLabel } from '@/components/ui/page-header';
import { ServerIcon, DatabaseIcon, CpuIcon, PlugIcon } from '@/components/ui/icons';
import { STATIC_SERVICES, type ServiceStatus } from '@/features/dashboard/mock-data';

const STATUS_DOT: Record<ServiceStatus, string> = {
  operational: 'bg-sage-500',
  degraded: 'bg-amber-400',
  offline: 'bg-red-500',
  pending: 'bg-stone-700',
};

const STATUS_LABEL: Record<ServiceStatus, string> = {
  operational: 'operational',
  degraded: 'degraded',
  offline: 'offline',
  pending: 'coming soon',
};

const ICONS: Record<string, React.ComponentType<{ size?: number }>> = {
  backend: ServerIcon,
  qdrant: DatabaseIcon,
  'ai-engine': CpuIcon,
  'llm-providers': PlugIcon,
};

export function PlatformHealth() {
  const [backendStatus, setBackendStatus] = useState<ServiceStatus>('pending');

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
    let cancelled = false;
    fetch(`${base}/health`)
      .then((res) => {
        if (!cancelled) setBackendStatus(res.ok ? 'operational' : 'degraded');
      })
      .catch(() => {
        if (!cancelled) setBackendStatus('offline');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const services = [
    { id: 'backend', label: 'Backend API', detail: 'FastAPI', status: backendStatus },
    ...STATIC_SERVICES,
  ];

  return (
    <div className="border border-ink-600 rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-ink-700">
        <SectionLabel>Platform Health</SectionLabel>
      </div>
      <div className="divide-y divide-ink-700">
        {services.map(({ id, label, detail, status }) => {
          const Icon = ICONS[id] ?? ServerIcon;
          return (
            <div key={id} className="flex items-center gap-3 px-5 py-3">
              <span className="text-stone-600 flex-shrink-0">
                <Icon size={13} />
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-stone-300 text-[12.5px]">{label}</p>
                <p className="font-mono text-stone-700 text-[10px]">{detail}</p>
              </div>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <span className={`w-1.5 h-1.5 rounded-full ${STATUS_DOT[status]}`} />
                <span className="font-mono text-stone-600 text-[10px]">
                  {STATUS_LABEL[status]}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
