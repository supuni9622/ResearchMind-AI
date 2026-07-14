export function StatTile({
  label,
  value,
  icon,
  sub,
}: {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  sub?: string;
}) {
  return (
    <div className="border border-ink-600 rounded-lg p-4">
      <div className="flex items-center gap-1.5 mb-3 text-stone-600">
        {icon}
        <span className="font-mono text-[10px] tracking-widest uppercase">{label}</span>
      </div>
      <p className="text-stone-100 text-2xl font-medium tabular-nums leading-none mb-1">
        {value}
      </p>
      {sub && <p className="text-stone-600 text-[11px]">{sub}</p>}
    </div>
  );
}
