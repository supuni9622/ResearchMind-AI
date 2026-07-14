interface IconProps {
  className?: string;
  size?: number;
}

const base = {
  fill: 'none' as const,
  'aria-hidden': true as const,
};

export function SearchIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.25" />
      <path d="M9.5 9.5L13 13" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
    </svg>
  );
}

export function FilterIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path
        d="M1.5 2h11l-4 5v4.5L6.5 13V7L1.5 2z"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ChevronRightIcon({ className, size = 12 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 12 12" {...base} className={className}>
      <path d="M4.5 2.5L8 6l-3.5 3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ChevronDownIcon({ className, size = 10 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 10 10" {...base} className={className}>
      <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function CloseIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

export function FileTextIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M8 1H3a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V5L8 1z" stroke="currentColor" strokeWidth="1.15" strokeLinejoin="round" />
      <path d="M8 1v4h4" stroke="currentColor" strokeWidth="1.15" strokeLinejoin="round" />
      <path d="M4.5 8h5M4.5 10.25h3.5" stroke="currentColor" strokeWidth="1.15" strokeLinecap="round" />
    </svg>
  );
}

export function LayersIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M7 1.5l5.5 2.75L7 7 1.5 4.25 7 1.5z" stroke="currentColor" strokeWidth="1.15" strokeLinejoin="round" />
      <path d="M1.5 7.25L7 10l5.5-2.75M1.5 9.75L7 12.5l5.5-2.75" stroke="currentColor" strokeWidth="1.15" strokeLinejoin="round" />
    </svg>
  );
}

export function DatabaseIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <ellipse cx="7" cy="3" rx="5" ry="2" stroke="currentColor" strokeWidth="1.15" />
      <path d="M2 3v3.5c0 1.1 2.24 2 5 2s5-.9 5-2V3" stroke="currentColor" strokeWidth="1.15" />
      <path d="M2 6.5V10c0 1.1 2.24 2 5 2s5-.9 5-2V6.5" stroke="currentColor" strokeWidth="1.15" />
    </svg>
  );
}

export function ActivityIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M1 7h2.5l1.5-4 2 8 1.5-4H13" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ServerIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <rect x="1.5" y="1.5" width="11" height="4.5" rx="0.75" stroke="currentColor" strokeWidth="1.15" />
      <rect x="1.5" y="8" width="11" height="4.5" rx="0.75" stroke="currentColor" strokeWidth="1.15" />
      <circle cx="4" cy="3.75" r="0.6" fill="currentColor" />
      <circle cx="4" cy="10.25" r="0.6" fill="currentColor" />
    </svg>
  );
}

export function CpuIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <rect x="3.5" y="3.5" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="1.15" />
      <rect x="6" y="6" width="2" height="2" stroke="currentColor" strokeWidth="1" />
      <path d="M5 1.5v2M9 1.5v2M5 10.5v2M9 10.5v2M1.5 5v2M1.5 9v2M12.5 5v2M12.5 9v2" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" />
    </svg>
  );
}

export function PlugIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M4.5 1.5v3M9.5 1.5v3M3 4.5h8v2a4 4 0 0 1-4 4 4 4 0 0 1-4-4v-2z" stroke="currentColor" strokeWidth="1.15" strokeLinejoin="round" />
      <path d="M7 10.5V13" stroke="currentColor" strokeWidth="1.15" strokeLinecap="round" />
    </svg>
  );
}

export function UploadIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M7 10V2M3.5 5.5L7 2l3.5 3.5M1.5 11.5h11" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function MessageIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M1.5 3a1.5 1.5 0 0 1 1.5-1.5h8A1.5 1.5 0 0 1 12.5 3v5a1.5 1.5 0 0 1-1.5 1.5H5l-3 2.5V3z" stroke="currentColor" strokeWidth="1.15" strokeLinejoin="round" />
    </svg>
  );
}

export function SparklesIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M7 1.5l1.1 3.4L11.5 6l-3.4 1.1L7 10.5l-1.1-3.4L2.5 6l3.4-1.1L7 1.5z" stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round" />
      <path d="M11.75 8.5l.5 1.5 1.5.5-1.5.5-.5 1.5-.5-1.5-1.5-.5 1.5-.5.5-1.5z" stroke="currentColor" strokeWidth="1" strokeLinejoin="round" />
    </svg>
  );
}

export function NetworkIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <circle cx="7" cy="2.5" r="1.5" stroke="currentColor" strokeWidth="1.1" />
      <circle cx="2.5" cy="11" r="1.5" stroke="currentColor" strokeWidth="1.1" />
      <circle cx="11.5" cy="11" r="1.5" stroke="currentColor" strokeWidth="1.1" />
      <path d="M7 4v3M7 7l-3.7 2.7M7 7l3.7 2.7" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" />
    </svg>
  );
}

export function ClockIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.15" />
      <path d="M7 4v3.2l2.2 1.3" stroke="currentColor" strokeWidth="1.15" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function TagIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M7.5 1.5H12v4.5L6 12 1.5 7.5l6-6z" stroke="currentColor" strokeWidth="1.15" strokeLinejoin="round" />
      <circle cx="9.5" cy="4" r="0.85" fill="currentColor" />
    </svg>
  );
}

export function CheckCircleIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.15" />
      <path d="M4.5 7.2l1.7 1.7 3.3-3.9" stroke="currentColor" strokeWidth="1.15" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function AlertIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M7 1.5l6 10.5H1L7 1.5z" stroke="currentColor" strokeWidth="1.15" strokeLinejoin="round" />
      <path d="M7 5.5v2.7" stroke="currentColor" strokeWidth="1.15" strokeLinecap="round" />
      <circle cx="7" cy="10.2" r="0.6" fill="currentColor" />
    </svg>
  );
}

export function TargetIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.1" />
      <circle cx="7" cy="7" r="3" stroke="currentColor" strokeWidth="1.1" />
      <circle cx="7" cy="7" r="0.75" fill="currentColor" />
    </svg>
  );
}

export function ZapIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M7.5 1.5L3 8h3.2l-.7 4.5L11 6H7.8l-.3-4.5z" stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round" />
    </svg>
  );
}

export function ShieldIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M7 1.5l4.5 1.6v3.4c0 3-1.9 5.1-4.5 6-2.6-.9-4.5-3-4.5-6V3.1L7 1.5z" stroke="currentColor" strokeWidth="1.15" strokeLinejoin="round" />
    </svg>
  );
}

export function ArrowDownIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M7 1.5v9.5M3.3 7.8L7 11.5l3.7-3.7" stroke="currentColor" strokeWidth="1.15" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function BookIcon({ className, size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" {...base} className={className}>
      <path d="M2 2.5c1.5-.7 3.3-.7 5 0v9c-1.7-.7-3.5-.7-5 0v-9zM12 2.5c-1.5-.7-3.3-.7-5 0v9c1.7-.7 3.5-.7 5 0v-9z" stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round" />
    </svg>
  );
}
