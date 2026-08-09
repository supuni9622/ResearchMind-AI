'use client';

import { useEffect, useState } from 'react';
import {
  api,
  PROVIDER_LABELS,
  PROVIDER_OPTIONS,
  type GenerationProvider,
} from '@/lib/api';

type ProviderOption = {
  value: GenerationProvider | 'auto';
  label: string;
};

export function useProviderOptions(): ProviderOption[] {
  const [options, setOptions] = useState<ProviderOption[]>(PROVIDER_OPTIONS);

  useEffect(() => {
    let cancelled = false;

    api.generation
      .providers()
      .then((providers) => {
        if (!cancelled) {
          setOptions([
            { value: 'auto', label: 'Auto' },
            ...providers.map((provider) => ({
              value: provider,
              label: PROVIDER_LABELS[provider],
            })),
          ]);
        }
      })
      .catch(() => {
        // Keep the cloud-provider fallback when capability discovery is unavailable.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return options;
}
