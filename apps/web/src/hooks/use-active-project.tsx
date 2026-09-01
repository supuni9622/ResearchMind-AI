'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { api, type Project } from '@/lib/api';
import {
  clearStoredActiveProjectId,
  getStoredActiveProjectId,
  setStoredActiveProjectId,
} from '@/lib/active-project';
import { useAuth } from '@/hooks/use-auth';

interface ActiveProjectState {
  projects: Project[];
  activeProjectId: string | null;
  activeProject: Project | null;
  loading: boolean;
  refresh: () => Promise<void>;
  setActiveProjectId: (projectId: string | null) => void;
  createProject: (name: string, description?: string | null) => Promise<Project>;
}

const ActiveProjectContext = createContext<ActiveProjectState | null>(null);

export function ActiveProjectProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectIdState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!isAuthenticated) {
      setProjects([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const { projects: fetched } = await api.projects.list();
      setProjects(fetched);

      const stored = getStoredActiveProjectId();
      if (stored && fetched.some((project) => project.id === stored)) {
        setActiveProjectIdState(stored);
      } else if (stored) {
        // Stored id no longer accessible (deleted, or access revoked) --
        // fall back to Personal rather than silently retrying forever.
        clearStoredActiveProjectId();
        setActiveProjectIdState(null);
      }
    } catch (err) {
      console.error('[ResearchMind] failed to load projects:', err);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const setActiveProjectId = useCallback((projectId: string | null) => {
    setActiveProjectIdState(projectId);
    if (projectId) {
      setStoredActiveProjectId(projectId);
    } else {
      clearStoredActiveProjectId();
    }
  }, []);

  const createProject = useCallback(
    async (name: string, description?: string | null) => {
      const project = await api.projects.create({ name, description });
      setProjects((prev) => [...prev, project]);
      setActiveProjectId(project.id);
      return project;
    },
    [setActiveProjectId]
  );

  const activeProject = projects.find((project) => project.id === activeProjectId) ?? null;

  return (
    <ActiveProjectContext.Provider
      value={{
        projects,
        activeProjectId,
        activeProject,
        loading,
        refresh,
        setActiveProjectId,
        createProject,
      }}
    >
      {children}
    </ActiveProjectContext.Provider>
  );
}

export function useActiveProject(): ActiveProjectState {
  const ctx = useContext(ActiveProjectContext);
  if (!ctx) throw new Error('useActiveProject must be used within ActiveProjectProvider');
  return ctx;
}
