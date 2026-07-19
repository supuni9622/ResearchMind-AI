'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';

const NAV_ITEMS = [
  {
    href: '/dashboard',
    label: 'Dashboard',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
        <rect x="1" y="1" width="5.5" height="5.5" rx="0.75" stroke="currentColor" strokeWidth="1.2" />
        <rect x="8.5" y="1" width="5.5" height="5.5" rx="0.75" stroke="currentColor" strokeWidth="1.2" />
        <rect x="1" y="8.5" width="5.5" height="5.5" rx="0.75" stroke="currentColor" strokeWidth="1.2" />
        <rect x="8.5" y="8.5" width="5.5" height="5.5" rx="0.75" stroke="currentColor" strokeWidth="1.2" />
      </svg>
    ),
  },
  {
    href: '/chat',
    label: 'Chat',
    icon: (
      <svg width="15" height="15" viewBox="0 0 14 14" fill="none" aria-hidden="true">
        <path
          d="M1.5 3a1.5 1.5 0 0 1 1.5-1.5h8A1.5 1.5 0 0 1 12.5 3v5a1.5 1.5 0 0 1-1.5 1.5H5l-3 2.5V3z"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    href: '/research',
    label: 'Research',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
        <circle cx="6.5" cy="6.5" r="5" stroke="currentColor" strokeWidth="1.2" />
        <path d="M10.5 10.5l3 3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    href: '/documents',
    label: 'Documents',
    icon: (
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden="true">
        <path
          d="M8.5 1H3a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1V5.5L8.5 1z"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinejoin="round"
        />
        <path d="M8.5 1v4.5H13" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
        <path d="M4.5 8.5h6M4.5 11h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    ),
  },
] as const;

function LogoMark() {
  return (
    <div className="w-6 h-6 rounded bg-sage-600 flex items-center justify-center flex-shrink-0">
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
        <path d="M1 1h4v4H1zM7 1h4v4H7zM1 7h4v4H1zM9 7a2 2 0 1 1 0 4 2 2 0 0 1 0-4z" fill="white" />
      </svg>
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="w-52 flex-shrink-0 border-r border-ink-600 bg-ink-900 flex flex-col min-h-screen">
      <div className="px-4 py-4 border-b border-ink-600">
        <div className="flex items-center gap-2">
          <LogoMark />
          <span className="text-stone-200 text-[13px] font-medium tracking-wide">
            ResearchMind
          </span>
        </div>
      </div>

      <nav className="flex-1 px-2 py-3">
        <ul className="space-y-0.5" role="list">
          {NAV_ITEMS.map(({ href, label, icon }) => {
            const active =
              pathname === href || pathname.startsWith(`${href}/`);
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] transition-colors duration-100 ${
                    active
                      ? 'bg-ink-700 text-stone-100'
                      : 'text-stone-400 hover:text-stone-200 hover:bg-ink-700/60'
                  }`}
                >
                  <span className={active ? 'text-sage-400' : 'text-stone-600'}>
                    {icon}
                  </span>
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {user && (
        <div className="border-t border-ink-600 px-3 py-3">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-sage-700 flex items-center justify-center flex-shrink-0">
              <span className="text-stone-100 text-[10px] font-semibold uppercase">
                {(user.full_name ?? user.email).charAt(0)}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-stone-300 text-[12px] font-medium truncate">
                {user.full_name ?? user.username}
              </p>
              <p className="font-mono text-stone-600 text-[10px] truncate">
                {user.email}
              </p>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="flex-shrink-0 p-1 text-stone-600 hover:text-stone-300 rounded transition-colors"
            >
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
                <path
                  d="M8.5 1H10a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H8.5M5 9l3.5-2.5L5 4M9 6.5H1"
                  stroke="currentColor"
                  strokeWidth="1.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
