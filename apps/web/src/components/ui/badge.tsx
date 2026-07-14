type BadgeTone = 'neutral' | 'sage' | 'amber' | 'red';

const TONE_STYLES: Record<BadgeTone, string> = {
  neutral: 'bg-ink-700 text-stone-400',
  sage: 'bg-sage-800/60 text-sage-400',
  amber: 'bg-amber-500/20 text-amber-400',
  red: 'bg-red-900/30 text-red-400',
};

export function Badge({
  children,
  tone = 'neutral',
  className = '',
}: {
  children: React.ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={`font-mono text-[10px] px-2 py-0.5 rounded-full whitespace-nowrap ${TONE_STYLES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

export function Pill({
  children,
  active = false,
  onClick,
  icon,
}: {
  children: React.ReactNode;
  active?: boolean;
  onClick?: () => void;
  icon?: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[12px] font-medium transition-colors duration-100 ${
        active
          ? 'bg-sage-800/60 text-sage-300 border border-sage-700/50'
          : 'bg-transparent text-stone-500 border border-ink-600 hover:border-ink-400 hover:text-stone-300'
      }`}
    >
      {icon}
      {children}
    </button>
  );
}
