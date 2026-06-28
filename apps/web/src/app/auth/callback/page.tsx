'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { exchangeCode, storeToken } from '@/lib/auth';

function Spinner() {
  return (
    <div className="w-7 h-7 border-2 border-sage-800 border-t-sage-500 rounded-full animate-spin" />
  );
}

function CallbackHandler() {
  const router = useRouter();
  const params = useSearchParams();
  const handled = useRef(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    const errorParam = params.get('error');
    if (errorParam) {
      setError(
        params.get('error_description') ?? 'Authentication was cancelled or failed.'
      );
      return;
    }

    const code = params.get('code');
    if (!code) {
      setError('No authorization code received.');
      return;
    }

    exchangeCode(code)
      .then(({ id_token }) => {
        storeToken(id_token);
        router.replace('/dashboard');
      })
      .catch((err: Error) => setError(err.message));
  }, [params, router]);

  if (error) {
    return (
      <div className="min-h-screen bg-ink-950 flex items-center justify-center px-6">
        <div className="max-w-sm w-full text-center">
          <div className="w-10 h-10 rounded-full bg-red-900/40 border border-red-800/50 flex items-center justify-center mx-auto mb-5">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="6.5" stroke="#E05C5C" strokeWidth="1.5" />
              <path
                d="M8 5v3.5M8 11h.01"
                stroke="#E05C5C"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <h1 className="text-stone-100 font-medium mb-2">Sign in failed</h1>
          <p className="text-stone-400 text-sm mb-7 leading-relaxed">{error}</p>
          <Link href="/" className="text-sage-400 hover:text-sage-300 text-sm transition-colors">
            ← Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-ink-950 flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <Spinner />
        <p className="font-mono text-stone-500 text-xs">Signing you in…</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-ink-950 flex items-center justify-center">
          <Spinner />
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  );
}
