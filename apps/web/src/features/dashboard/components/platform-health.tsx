'use client';

import { useEffect, useState } from 'react';
import { SectionLabel } from '@/components/ui/page-header';
import { ServerIcon, DatabaseIcon, CpuIcon, PlugIcon } from '@/components/ui/icons';
import { api, type InfrastructureServiceStatus } from '@/lib/api';

type DisplayStatus = 'operational' | 'degraded' | 'offline';

const STATUS_DOT: Record<DisplayStatus, string> = {
  operational: 'bg-sage-500',
  degraded: 'bg-amber-400',
  offline: 'bg-red-500',
};

const STATUS_LABEL: Record<DisplayStatus, string> = {
  operational: 'operational',
  degraded: 'degraded',
  offline: 'offline',
};

const ICONS: Record<string, React.ComponentType<{ size?: number }>> = {
  backend: ServerIcon,
  qdrant: DatabaseIcon,
  'ai-engine': CpuIcon,
  'llm-providers': PlugIcon,
};

export function PlatformHealth() {
  const [health, setHealth] = useState<{
    status: InfrastructureServiceStatus;
    services: Record<'postgres' | 'valkey' | 'qdrant', InfrastructureServiceStatus>;
  } | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.health
      .get()
      .then((result) => {
        if (!cancelled) setHealth(result);
      })
      .catch(() => {
        if (!cancelled) {
          setHealth({
            status: 'unhealthy',
            services: { postgres: 'unhealthy', valkey: 'unhealthy', qdrant: 'unhealthy' },
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const displayStatus = (status: InfrastructureServiceStatus | undefined): DisplayStatus => {
    if (status === 'healthy') return 'operational';
    if (health === null) return 'degraded';
    return 'offline';
  };

  const services = [
    { id: 'backend', label: 'Backend API', detail: 'FastAPI', status: displayStatus(health?.status) },
    { id: 'postgres', label: 'PostgreSQL', detail: 'Primary database', status: displayStatus(health?.services.postgres) },
    { id: 'valkey', label: 'Valkey', detail: 'Cache and session memory', status: displayStatus(health?.services.valkey) },
    { id: 'qdrant', label: 'Qdrant', detail: 'Vector store', status: displayStatus(health?.services.qdrant) },
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
