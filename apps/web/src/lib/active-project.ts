// Persists which workspace (project) is currently active, across browser
// sessions/tabs -- unlike the auth token (`lib/auth.ts`, sessionStorage,
// per-tab), "which workspace" should survive a closed tab or a restart, so
// this uses localStorage. Same SSR-safe idiom as `lib/auth.ts`: guard on
// `typeof window`, swallow storage errors (private browsing, quota).

const ACTIVE_PROJECT_KEY = 'rm_active_project_id';

export function getStoredActiveProjectId(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(ACTIVE_PROJECT_KEY);
  } catch {
    return null;
  }
}

export function setStoredActiveProjectId(projectId: string): void {
  try {
    localStorage.setItem(ACTIVE_PROJECT_KEY, projectId);
  } catch {}
}

export function clearStoredActiveProjectId(): void {
  try {
    localStorage.removeItem(ACTIVE_PROJECT_KEY);
  } catch {}
}
