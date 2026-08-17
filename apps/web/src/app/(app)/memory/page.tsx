'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { EmptyState } from '@/components/ui/empty-state';
import { PageHeader, SectionLabel } from '@/components/ui/page-header';
import { RefreshIcon, SearchIcon } from '@/components/ui/icons';
import {
  api,
  type MemoryProject,
  type MemoryRecord,
  type MemoryScopeSettings,
  type MemoryType,
} from '@/lib/api';

const PAGE_SIZE = 10;
type Scope = 'personal' | 'project';
type Origin = 'all' | 'explicit' | 'inferred';
type TypeFilter = 'all' | Exclude<MemoryType, 'session'>;

function formatDate(value: string | null) {
  if (!value) return 'Never';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value)
  );
}

function typeLabel(type: MemoryType) {
  return { user: 'Preference', semantic: 'Semantic fact', research: 'Research finding', session: 'Temporary' }[type];
}

function Toggle({ checked, disabled, label, onChange }: { checked: boolean; disabled?: boolean; label: string; onChange: (value: boolean) => void }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} disabled={disabled} onClick={() => onChange(!checked)} className={`relative h-6 w-11 rounded-full border transition-colors focus:outline-none focus:ring-2 focus:ring-sage-600 ${checked ? 'border-sage-600 bg-sage-700' : 'border-ink-500 bg-ink-700'} disabled:opacity-40`}>
      <span className={`absolute top-[3px] h-4 w-4 rounded-full bg-stone-100 transition-transform ${checked ? 'translate-x-5' : 'translate-x-1'}`} />
    </button>
  );
}

export default function MemoryPage() {
  const [scope, setScope] = useState<Scope>('personal');
  const [projects, setProjects] = useState<MemoryProject[]>([]);
  const [projectId, setProjectId] = useState('');
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [type, setType] = useState<TypeFilter>('all');
  const [origin, setOrigin] = useState<Origin>('all');
  const [source, setSource] = useState('');
  const [createdFrom, setCreatedFrom] = useState('');
  const [updatedFrom, setUpdatedFrom] = useState('');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<MemoryScopeSettings | null>(null);
  const [settingsBusy, setSettingsBusy] = useState(false);
  const [editing, setEditing] = useState<MemoryRecord | null>(null);
  const [draft, setDraft] = useState('');
  const [reviewEdit, setReviewEdit] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<MemoryRecord[]>([]);
  const [mutating, setMutating] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const dialogCancelRef = useRef<HTMLButtonElement>(null);
  const requestIdRef = useRef(0);

  const selectedProject = projects.find((project) => project.id === projectId);
  const activeProjectId = scope === 'project' ? projectId || undefined : undefined;
  const canLoad = scope === 'personal' || Boolean(activeProjectId);

  const query = useMemo(() => ({
    search: debouncedSearch || undefined,
    type: type === 'all' ? undefined : [type],
    origin: origin === 'all' ? undefined : origin,
    source: source || undefined,
    created_from: createdFrom ? new Date(`${createdFrom}T00:00:00`).toISOString() : undefined,
    updated_from: updatedFrom ? new Date(`${updatedFrom}T00:00:00`).toISOString() : undefined,
    scope_type: scope,
    project_id: activeProjectId,
  }), [activeProjectId, createdFrom, debouncedSearch, origin, scope, source, type, updatedFrom]);

  const loadProjects = useCallback(async () => {
    try {
      const result = await api.memory.projects();
      setProjects(result);
      setProjectId((current) => current || result[0]?.id || '');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    }
  }, []);

  const load = useCallback(async () => {
    if (!canLoad) { setMemories([]); setTotal(0); setLoading(false); return; }
    const requestId = ++requestIdRef.current;
    setRefreshing(true);
    try {
      const [list, currentSettings] = await Promise.all([
        api.memory.list({ ...query, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }),
        api.memory.getSettings(scope, activeProjectId),
      ]);
      if (requestId !== requestIdRef.current) return;
      setMemories(list.memories); setTotal(list.total); setSettings(currentSettings); setError(null);
      setSelected(new Set());
    } catch (err) {
      if (requestId === requestIdRef.current) setError(err instanceof Error ? err.message : 'Failed to load memory');
    } finally {
      if (requestId === requestIdRef.current) { setLoading(false); setRefreshing(false); }
    }
  }, [activeProjectId, canLoad, page, query, scope]);

  useEffect(() => { void loadProjects(); }, [loadProjects]);
  useEffect(() => { const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 300); return () => window.clearTimeout(timer); }, [search]);
  useEffect(() => { setPage(1); }, [createdFrom, debouncedSearch, origin, scope, source, type, updatedFrom, projectId]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!pendingDelete.length && !reviewEdit) return;
    dialogCancelRef.current?.focus();
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape' && !mutating) { setPendingDelete([]); setReviewEdit(false); } };
    window.addEventListener('keydown', close); return () => window.removeEventListener('keydown', close);
  }, [mutating, pendingDelete.length, reviewEdit]);

  function clearFilters() { setSearch(''); setType('all'); setOrigin('all'); setSource(''); setCreatedFrom(''); setUpdatedFrom(''); }

  async function updateSettings(next: Partial<Pick<MemoryScopeSettings, 'capture_enabled' | 'inherit_personal_memory'>>) {
    if (!settings) return;
    setSettingsBusy(true);
    try {
      const updated = await api.memory.updateSettings({
        scope_type: scope, project_id: activeProjectId ?? null,
        capture_enabled: next.capture_enabled ?? settings.capture_enabled,
        retrieval_enabled: settings.retrieval_enabled,
        inherit_personal_memory: next.inherit_personal_memory ?? settings.inherit_personal_memory,
      });
      setSettings(updated); setError(null);
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to update memory settings'); }
    finally { setSettingsBusy(false); }
  }

  async function saveEdit() {
    if (!editing || !draft.trim()) return;
    setMutating(true);
    try {
      const updated = await api.memory.update(editing, draft.trim());
      setMemories((items) => items.map((item) => item.id === updated.id ? updated : item));
      setEditing(null); setReviewEdit(false); setError(null);
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to update memory'); }
    finally { setMutating(false); }
  }

  async function deleteMemories() {
    setMutating(true);
    let deleted = 0;
    try {
      for (const memory of pendingDelete) { await api.memory.delete(memory); deleted += 1; }
      setPendingDelete([]); setSelected(new Set()); await load();
    } catch (err) {
      setError(`${err instanceof Error ? err.message : 'Failed to delete memory'}${deleted ? ` (${deleted} deleted before the error.)` : ''}`);
      setPendingDelete([]); await load();
    } finally { setMutating(false); }
  }

  async function exportScope() {
    setRefreshing(true);
    try {
      const all: MemoryRecord[] = [];
      let offset = 0;
      while (true) {
        const batch = await api.memory.list({ ...query, limit: 100, offset });
        all.push(...batch.memories); offset += batch.memories.length;
        if (offset >= batch.total || batch.memories.length === 0) break;
      }
      const blob = new Blob([JSON.stringify({ exported_at: new Date().toISOString(), scope, project: selectedProject ?? null, memories: all }, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob); const anchor = document.createElement('a');
      anchor.href = url; anchor.download = `researchmind-${scope}-memory.json`; anchor.click(); URL.revokeObjectURL(url);
    } catch (err) { setError(err instanceof Error ? err.message : 'Failed to export memory'); }
    finally { setRefreshing(false); }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filtered = Boolean(search || type !== 'all' || origin !== 'all' || source || createdFrom || updatedFrom);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-8 sm:py-10">
      <PageHeader eyebrow="Personalization" title="Memory" actions={<button type="button" onClick={() => void load()} disabled={refreshing} className="flex items-center gap-1.5 rounded-lg border border-ink-600 px-3 py-1.5 text-[13px] text-stone-400 hover:text-stone-200 disabled:opacity-40"><RefreshIcon size={13} className={refreshing ? 'animate-spin' : ''} />Refresh</button>} />

      <div className="mb-6 inline-flex rounded-xl border border-ink-600 bg-ink-900 p-1" role="tablist" aria-label="Memory scope">
        {(['personal', 'project'] as const).map((item) => <button key={item} role="tab" aria-selected={scope === item} onClick={() => setScope(item)} className={`rounded-lg px-4 py-2 text-[13px] capitalize ${scope === item ? 'bg-sage-800 text-stone-100 shadow-sm' : 'text-stone-500 hover:text-stone-300'}`}>{item} memory</button>)}
      </div>

      {scope === 'personal' ? (
        <div className="mb-6 rounded-xl border border-sage-900 bg-gradient-to-r from-sage-950/60 to-ink-800 px-5 py-4">
          <p className="text-[13px] font-medium text-stone-200">Your memory, available across ResearchMind</p>
          <p className="mt-1 max-w-3xl text-[12px] leading-5 text-stone-500">Personal preferences and permitted cross-project facts may be used in Chat and Research. Projects inherit personal defaults unless you disable inheritance for that project.</p>
        </div>
      ) : (
        <div className="mb-6 rounded-xl border border-amber-900/70 bg-amber-950/20 px-5 py-4">
          <label htmlFor="memory-project" className="font-mono text-[10px] uppercase tracking-[0.16em] text-amber-400">Active isolation boundary</label>
          <select id="memory-project" value={projectId} onChange={(event) => setProjectId(event.target.value)} className="mt-2 block w-full max-w-md rounded-lg border border-ink-500 bg-ink-900 px-3 py-2 text-[13px] text-stone-200 focus:border-sage-600 focus:outline-none"><option value="">Select a project</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.name} · {project.role}</option>)}</select>
          <p className="mt-2 text-[12px] text-stone-500">Only members of <span className="text-stone-300">{selectedProject?.name ?? 'the selected project'}</span> can access this memory. It is never retrieved for another project.</p>
        </div>
      )}

      {error && <div role="alert" className="mb-5 rounded-lg border border-red-900/70 bg-red-950/30 px-4 py-3 text-[13px] text-red-300">{error}</div>}

      {canLoad && settings && <section className="mb-7 grid gap-3 sm:grid-cols-2" aria-label="Memory controls">
        <div className="flex items-center justify-between rounded-xl border border-ink-600 bg-ink-800/40 p-4"><div><p className="text-[13px] text-stone-200">Capture new {scope} memory</p><p className="mt-1 text-[11px] text-stone-600">Turning this off keeps existing memories and retention unchanged.</p></div><Toggle label={`Capture new ${scope} memory`} checked={settings.capture_enabled} disabled={settingsBusy} onChange={(value) => void updateSettings({ capture_enabled: value })} /></div>
        {scope === 'project' ? <div className="flex items-center justify-between rounded-xl border border-ink-600 bg-ink-800/40 p-4"><div><p className="text-[13px] text-stone-200">Inherit personal defaults</p><p className="mt-1 text-[11px] text-stone-600">Allow personal USER preferences in this project.</p></div><Toggle label="Inherit personal defaults" checked={settings.inherit_personal_memory} disabled={settingsBusy} onChange={(value) => void updateSettings({ inherit_personal_memory: value })} /></div> : <div className="rounded-xl border border-ink-600 bg-ink-800/40 p-4"><p className="text-[13px] text-stone-200">Existing memory remains visible</p><p className="mt-1 text-[11px] text-stone-600">Capture, retrieval, and lifecycle retention are separate controls.</p></div>}
      </section>}

      <section aria-labelledby="memory-list-heading">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3"><div id="memory-list-heading"><SectionLabel count={total}>{scope === 'personal' ? 'What ResearchMind knows about you' : `${selectedProject?.name ?? 'Project'} memory`}</SectionLabel></div><div className="flex gap-2"><button type="button" onClick={() => void exportScope()} disabled={!canLoad || refreshing} className="rounded-lg border border-ink-600 px-3 py-1.5 text-[12px] text-stone-400 hover:text-stone-200 disabled:opacity-40">Export scope</button><button type="button" onClick={() => setPendingDelete(memories.filter((memory) => selected.has(memory.id)))} disabled={selected.size === 0} className="rounded-lg border border-red-900/70 px-3 py-1.5 text-[12px] text-red-400 disabled:opacity-35">Delete selected ({selected.size})</button></div></div>

        <div className="mb-5 grid gap-2 rounded-xl border border-ink-600 bg-ink-800/30 p-3 sm:grid-cols-2 lg:grid-cols-7">
          <label className="relative sm:col-span-2"><span className="sr-only">Search memories</span><span className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-600"><SearchIcon size={13} /></span><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search memories…" className="w-full rounded-lg border border-ink-600 bg-ink-900 py-2 pl-8 pr-3 text-[12px] text-stone-200 focus:border-sage-600 focus:outline-none" /></label>
          <select aria-label="Memory type" value={type} onChange={(event) => setType(event.target.value as TypeFilter)} className="rounded-lg border border-ink-600 bg-ink-900 px-2 py-2 text-[12px] text-stone-300"><option value="all">All types</option><option value="user">Preferences</option><option value="semantic">Semantic facts</option><option value="research">Research findings</option></select>
          <select aria-label="Memory origin" value={origin} onChange={(event) => setOrigin(event.target.value as Origin)} className="rounded-lg border border-ink-600 bg-ink-900 px-2 py-2 text-[12px] text-stone-300"><option value="all">Any origin</option><option value="explicit">Explicitly provided</option><option value="inferred">Inferred</option></select>
          <input aria-label="Filter by source" value={source} onChange={(event) => setSource(event.target.value)} placeholder="Source" className="rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-[12px] text-stone-300 placeholder:text-stone-600" />
          <input aria-label="Created since" title="Created since" type="date" value={createdFrom} onChange={(event) => setCreatedFrom(event.target.value)} className="rounded-lg border border-ink-600 bg-ink-900 px-2 py-2 text-[12px] text-stone-400" />
          <input aria-label="Updated since" type="date" value={updatedFrom} onChange={(event) => setUpdatedFrom(event.target.value)} className="rounded-lg border border-ink-600 bg-ink-900 px-2 py-2 text-[12px] text-stone-400" />
        </div>

        {!canLoad ? <EmptyState title="Choose a project" description={projects.length ? 'Select an authorized project to review its isolated memory.' : 'No project memberships are available yet.'} /> : loading ? <div className="py-16 text-center text-[13px] text-stone-600">Loading memory…</div> : memories.length === 0 ? <EmptyState title={filtered ? 'No matching memories' : 'Nothing remembered in this scope'} description={filtered ? 'Try changing or clearing the filters.' : `Eligible ${scope} memories will appear here after capture.`} action={filtered ? <button type="button" onClick={clearFilters} className="rounded-lg border border-ink-500 px-3 py-1.5 text-[12px] text-stone-300">Clear filters</button> : undefined} /> : (
          <ul className="space-y-3" role="list">{memories.map((memory) => <li key={memory.id} className="rounded-xl border border-ink-600 bg-ink-800/40 p-4 hover:border-ink-500 sm:p-5"><div className="flex gap-3"><input type="checkbox" aria-label={`Select memory: ${memory.content}`} checked={selected.has(memory.id)} onChange={(event) => setSelected((current) => { const next = new Set(current); event.target.checked ? next.add(memory.id) : next.delete(memory.id); return next; })} className="mt-1 accent-sage-600" /><div className="min-w-0 flex-1">{editing?.id === memory.id ? <div><textarea autoFocus value={draft} maxLength={10000} rows={4} onChange={(event) => setDraft(event.target.value)} className="w-full resize-y rounded-lg border border-sage-800 bg-ink-900 px-3 py-2 text-[14px] leading-6 text-stone-200 focus:outline-none" /><p className="mt-1 text-right font-mono text-[10px] text-stone-600">{draft.trim().length}/10,000</p></div> : <p className="whitespace-pre-wrap text-[14px] leading-6 text-stone-200">{memory.content}</p>}</div></div>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-ink-700 pt-3"><div className="flex flex-wrap gap-1.5 font-mono text-[10px]"><span className="rounded bg-sage-950 px-2 py-1 text-sage-400">{typeLabel(memory.type)}</span><span className={`rounded px-2 py-1 ${memory.origin === 'explicit' ? 'bg-blue-950/60 text-blue-300' : 'bg-violet-950/60 text-violet-300'}`}>{memory.origin === 'explicit' ? 'Explicitly provided' : 'Inferred by ResearchMind'}</span>{memory.source && <span className="rounded bg-ink-700 px-2 py-1 text-stone-400">Source: {memory.source}</span>}{memory.confidence != null && <span className="rounded bg-ink-700 px-2 py-1 text-stone-400">Confidence {Math.round(memory.confidence * 100)}%</span>}</div><div className="flex items-center gap-1">{editing?.id === memory.id ? <><button type="button" onClick={() => setEditing(null)} className="px-2 py-1.5 text-[12px] text-stone-500">Cancel</button><button type="button" disabled={!draft.trim() || draft.trim() === memory.content} onClick={() => setReviewEdit(true)} className="rounded-md bg-sage-700 px-3 py-1.5 text-[12px] text-white disabled:opacity-40">Review change</button></> : <><button type="button" disabled={!memory.editable} onClick={() => { setEditing(memory); setDraft(memory.content); }} className="px-2 py-1.5 text-[12px] text-stone-500 hover:text-stone-200 disabled:opacity-35">Edit</button><button type="button" onClick={() => setPendingDelete([memory])} className="rounded-md px-2 py-1.5 text-[12px] text-stone-600 hover:bg-red-950/30 hover:text-red-400">Forget</button></>}</div></div>
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 font-mono text-[10px] text-stone-600"><span>Updated {formatDate(memory.updated_at)}</span><span>Last used {formatDate(memory.last_used_at)}</span><span>Created {formatDate(memory.created_at)}</span></div>
          </li>)}</ul>
        )}

        {!loading && total > 0 && <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-ink-700 pt-4"><p className="font-mono text-[10px] text-stone-600">Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}</p><div className="flex items-center gap-2"><button type="button" disabled={page === 1 || refreshing} onClick={() => setPage((value) => value - 1)} className="rounded-lg border border-ink-600 px-3 py-1.5 text-[12px] text-stone-400 disabled:opacity-35">Previous</button><span className="font-mono text-[10px] text-stone-500">{page} / {totalPages}</span><button type="button" disabled={page >= totalPages || refreshing} onClick={() => setPage((value) => value + 1)} className="rounded-lg border border-ink-600 px-3 py-1.5 text-[12px] text-stone-400 disabled:opacity-35">Next</button></div></div>}
      </section>

      {(pendingDelete.length > 0 || (reviewEdit && editing)) && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm" onMouseDown={(event) => { if (event.target === event.currentTarget && !mutating) { setPendingDelete([]); setReviewEdit(false); } }}><div role="alertdialog" aria-modal="true" aria-labelledby="memory-dialog-title" className="w-full max-w-lg overflow-hidden rounded-2xl border border-ink-500 bg-ink-800 shadow-2xl"><div className="border-b border-ink-600 px-5 py-5"><h2 id="memory-dialog-title" className="font-display text-lg text-stone-100">{reviewEdit ? 'Review the final memory' : pendingDelete.length > 1 ? `Forget ${pendingDelete.length} memories?` : 'Forget this memory?'}</h2><p className="mt-1 text-[12px] leading-5 text-stone-500">{reviewEdit ? 'Your correction becomes explicit and will be used in future eligible requests. Its scope will not change.' : 'ResearchMind will stop using the selected memory in future requests. This cannot be undone.'}</p></div><div className="max-h-64 overflow-y-auto px-5 py-4">{reviewEdit ? <div className="space-y-3"><div><p className="mb-1 font-mono text-[10px] uppercase text-stone-600">Before</p><p className="rounded-lg bg-ink-900 px-3 py-2 text-[13px] text-stone-500 line-through">{editing?.content}</p></div><div><p className="mb-1 font-mono text-[10px] uppercase text-sage-500">After</p><p className="rounded-lg border border-sage-900 bg-sage-950/30 px-3 py-2 text-[13px] text-stone-200">{draft.trim()}</p></div></div> : <ul className="space-y-2">{pendingDelete.map((memory) => <li key={memory.id} className="rounded-lg bg-ink-900 px-3 py-2 text-[13px] text-stone-300">“{memory.content}”</li>)}</ul>}</div><div className="flex justify-end gap-2 border-t border-ink-600 px-5 py-4"><button ref={dialogCancelRef} type="button" disabled={mutating} onClick={() => { setPendingDelete([]); setReviewEdit(false); }} className="rounded-lg border border-ink-500 px-4 py-2 text-[12px] text-stone-300 disabled:opacity-40">Cancel</button><button type="button" disabled={mutating} onClick={() => void (reviewEdit ? saveEdit() : deleteMemories())} className={`rounded-lg px-4 py-2 text-[12px] text-white disabled:opacity-50 ${reviewEdit ? 'bg-sage-700' : 'bg-red-800'}`}>{mutating ? 'Working…' : reviewEdit ? 'Confirm update' : 'Forget permanently'}</button></div></div></div>}
    </div>
  );
}
