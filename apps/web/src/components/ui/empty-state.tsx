export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="text-center py-16 border border-dashed border-ink-600 rounded-xl px-6">
      <p className="text-stone-400 text-sm mb-1">{title}</p>
      {description && <p className="text-stone-600 text-[13px]">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
