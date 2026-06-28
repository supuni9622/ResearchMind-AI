'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { buildLogoutUrl, clearToken, getStoredToken } from '@/lib/auth';
import { api, type UserProfile } from '@/lib/api';

interface AuthState {
  user: UserProfile | null;
  loading: boolean;
  isAuthenticated: boolean;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  // Only true when we're CERTAIN the session is gone (no token, or backend returned 401).
  // Transient network/server errors leave this false so the user isn't kicked out.
  const [isUnauthorized, setIsUnauthorized] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    const token = getStoredToken();

    if (!token) {
      // No token in storage — definitely not authenticated.
      setIsUnauthorized(true);
      setLoading(false);
      return;
    }

    try {
      const profile = await api.auth.me();
      setUser(profile);
      setIsUnauthorized(false);
    } catch (err) {
      const status = (err as Error & { status?: number }).status;

      // Log so the developer can see what's happening in DevTools.
      console.error('[ResearchMind] auth.me() failed:', err);

      if (status === 401) {
        // Token is genuinely invalid or expired — sign the user out.
        clearToken();
        setUser(null);
        setIsUnauthorized(true);
      }
      // For any other error (network down, 5xx, CORS) keep the session open.
      // The user stays on the page with user=null; they can retry.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function logout() {
    clearToken();
    setUser(null);
    setIsUnauthorized(true);
    const baseUrl = process.env.NEXT_PUBLIC_BASE_URL ?? window.location.origin;
    window.location.href = buildLogoutUrl(baseUrl);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        // Authenticated = we haven't positively determined the session is gone.
        isAuthenticated: !isUnauthorized,
        logout,
        refresh,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
