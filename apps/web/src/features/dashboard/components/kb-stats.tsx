import { StatTile } from '@/components/ui/stat-tile';
import { FileTextIcon, LayersIcon, DatabaseIcon, ActivityIcon } from '@/components/ui/icons';

export function KnowledgeBaseStats({
  documentCount,
  indexedChunkCount,
  embeddingCount,
  researchSessionCount,
  monthCostUsd,
  totalCostUsd,
}: {
  documentCount: number;
  indexedChunkCount: number | null;
  embeddingCount: number | null;
  researchSessionCount: number;
  monthCostUsd: number | null;
  totalCostUsd: number | null;
}) {
  const formatCost = (cost: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    }).format(cost);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
      <StatTile
        label="Documents"
        value={documentCount}
        icon={<FileTextIcon size={12} />}
      />
      <StatTile
        label="Indexed Chunks"
        value={indexedChunkCount ?? '—'}
        icon={<LayersIcon size={12} />}
        sub={indexedChunkCount === null ? 'not available' : 'in your knowledge base'}
      />
      <StatTile
        label="Embeddings"
        value={embeddingCount ?? '—'}
        icon={<DatabaseIcon size={12} />}
        sub={embeddingCount === null ? 'not available' : 'stored vectors'}
      />
      <StatTile
        label="Research Sessions"
        value={researchSessionCount}
        icon={<ActivityIcon size={12} />}
      />
      <StatTile
        label="AI Cost (Month)"
        value={monthCostUsd === null ? '—' : formatCost(monthCostUsd)}
        icon={<ActivityIcon size={12} />}
        sub={totalCostUsd === null ? 'not available' : `${formatCost(totalCostUsd)} all time`}
      />
    </div>
  );
}
