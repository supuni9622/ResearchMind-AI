import { StatTile } from '@/components/ui/stat-tile';
import { FileTextIcon, LayersIcon, DatabaseIcon, ActivityIcon } from '@/components/ui/icons';

export function KnowledgeBaseStats({
  documentCount,
}: {
  documentCount: number;
}) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <StatTile
        label="Documents"
        value={documentCount}
        icon={<FileTextIcon size={12} />}
      />
      <StatTile
        label="Chunks"
        value={documentCount > 0 ? (documentCount * 42).toLocaleString() : 0}
        icon={<LayersIcon size={12} />}
        sub="estimated"
      />
      <StatTile
        label="Embeddings"
        value={documentCount > 0 ? (documentCount * 42).toLocaleString() : 0}
        icon={<DatabaseIcon size={12} />}
        sub="estimated"
      />
      <StatTile
        label="Research Sessions"
        value={3}
        icon={<ActivityIcon size={12} />}
      />
    </div>
  );
}
