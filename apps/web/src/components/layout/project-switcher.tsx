'use client';

import { useState } from 'react';
import { useActiveProject } from '@/hooks/use-active-project';
import { Drawer } from '@/components/ui/drawer';
import { ChevronDownIcon } from '@/components/ui/icons';

export function ProjectSwitcher() {
  const { projects, activeProject, setActiveProjectId, createProject, loading } =
    useActiveProject();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      await createProject(name.trim(), description.trim() || null);
      setName('');
      setDescription('');
      setCreating(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the project.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="relative px-3 py-2 border-b border-ink-600">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={loading}
        className="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-[12px] text-stone-300 hover:bg-ink-700/60 transition-colors disabled:opacity-50"
      >
        <span className="truncate">{activeProject ? activeProject.name : 'Personal'}</span>
        <span className={`text-stone-600 transition-transform ${open ? 'rotate-180' : ''}`}>
          <ChevronDownIcon />
        </span>
      </button>

      {open && (
        <>
          <button
            type="button"
            aria-label="Close workspace switcher"
            className="fixed inset-0 z-40 cursor-default"
            onClick={() => setOpen(false)}
          />
          <div className="absolute left-3 right-3 top-full z-50 mt-1 rounded-lg border border-ink-600 bg-ink-800 shadow-xl overflow-hidden">
            <ul className="max-h-64 overflow-y-auto scrollbar-thin py-1" role="list">
              <li>
                <button
                  type="button"
                  onClick={() => {
                    setActiveProjectId(null);
                    setOpen(false);
                  }}
                  className={`block w-full truncate px-3 py-1.5 text-left text-[12px] ${
                    !activeProject
                      ? 'text-sage-400'
                      : 'text-stone-300 hover:bg-ink-700/60'
                  }`}
                >
                  Personal
                </button>
              </li>
              {projects.map((project) => (
                <li key={project.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setActiveProjectId(project.id);
                      setOpen(false);
                    }}
                    className={`block w-full truncate px-3 py-1.5 text-left text-[12px] ${
                      activeProject?.id === project.id
                        ? 'text-sage-400'
                        : 'text-stone-300 hover:bg-ink-700/60'
                    }`}
                  >
                    {project.name}
                  </button>
                </li>
              ))}
            </ul>
            <div className="border-t border-ink-600">
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  setCreating(true);
                }}
                className="block w-full px-3 py-1.5 text-left text-[12px] text-sage-500 hover:bg-ink-700/60"
              >
                + New project
              </button>
            </div>
          </div>
        </>
      )}

      <Drawer
        open={creating}
        onClose={() => setCreating(false)}
        title="New project"
        eyebrow="Workspace"
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <label className="block">
            <span className="mb-1.5 block text-[12px] text-stone-400">Name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
              required
              className="w-full bg-ink-800 border border-ink-600 rounded-lg px-3 py-1.5 text-stone-200 text-[13px] placeholder-stone-600 focus:outline-none focus:border-sage-600 transition-colors"
              placeholder="e.g. LoRA research"
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-[12px] text-stone-400">
              Description <span className="text-stone-600">(optional)</span>
            </span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full bg-ink-800 border border-ink-600 rounded-lg px-3 py-1.5 text-stone-200 text-[13px] placeholder-stone-600 focus:outline-none focus:border-sage-600 transition-colors resize-none"
              placeholder="What is this workspace for?"
            />
          </label>
          {error && <p className="text-[12px] text-red-300">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => setCreating(false)}
              className="rounded-lg border border-ink-500 px-4 py-2 text-[12px] text-stone-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !name.trim()}
              className="rounded-lg bg-sage-700 px-4 py-2 text-[12px] text-white disabled:opacity-40"
            >
              {submitting ? 'Creating…' : 'Create project'}
            </button>
          </div>
        </form>
      </Drawer>
    </div>
  );
}
