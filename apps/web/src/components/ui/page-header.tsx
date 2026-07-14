interface PageHeaderProps {
  eyebrow: string;
  title: string;
  size?: 'lg' | 'md';
  actions?: React.ReactNode;
}

export function PageHeader({ eyebrow, title, size = 'lg', actions }: PageHeaderProps) {
  return (
    <header className="mb-8 flex items-start justify-between gap-4">
      <div>
        <p className="font-mono text-stone-600 text-[10px] tracking-[0.2em] uppercase mb-2">
          {eyebrow}
        </p>
        <h1
          className="font-display text-stone-100 leading-tight"
          style={{
            fontSize: size === 'lg' ? '2.25rem' : '1.875rem',
            fontVariationSettings: `'opsz' ${size === 'lg' ? 48 : 40}, 'SOFT' 0, 'WONK' 0`,
          }}
        >
          {title}
        </h1>
      </div>
      {actions && <div className="flex-shrink-0 pt-1">{actions}</div>}
    </header>
  );
}

export function SectionLabel({
  children,
  count,
}: {
  children: React.ReactNode;
  count?: number | string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className="font-display text-amber-400"
        style={{ fontSize: '0.8125rem', fontVariationSettings: "'opsz' 20, 'SOFT' 0" }}
      >
        {children}
      </span>
      {count != null && <span className="font-mono text-stone-600 text-[10px]">{count}</span>}
    </div>
  );
}
