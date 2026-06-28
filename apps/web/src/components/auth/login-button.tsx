'use client';

import { buildLoginUrl } from '@/lib/auth';

interface LoginButtonProps {
  variant?: 'primary' | 'ghost';
}

export function LoginButton({ variant = 'primary' }: LoginButtonProps) {
  function handleLogin() {
    window.location.href = buildLoginUrl();
  }

  if (variant === 'ghost') {
    return (
      <button
        onClick={handleLogin}
        className="text-stone-400 hover:text-stone-100 text-sm transition-colors duration-150"
      >
        Sign in →
      </button>
    );
  }

  return (
    <button
      onClick={handleLogin}
      className="inline-flex items-center gap-2 bg-sage-600 hover:bg-sage-500 text-stone-100 text-sm font-medium px-6 py-3 rounded-lg transition-colors duration-150"
    >
      Sign in with your account
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
        <path
          d="M2 7h10M8 3l4 4-4 4"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}
