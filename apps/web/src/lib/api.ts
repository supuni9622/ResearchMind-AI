import { getStoredToken } from './auth';
import { extractErrorMessage } from './errors';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  if (init?.headers) {
    Object.assign(headers, init.headers);
  }

  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const msg = extractErrorMessage(body, `${res.status} ${res.statusText}`);
    const err = new Error(msg) as Error & { status: number };
    err.status = res.status;
    throw err;
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  provider: string;
  verified: boolean;
}

export type DocumentUploadStatus = 'pending' | 'uploading' | 'completed' | 'failed';
export type DocumentProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Document {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  upload_status: DocumentUploadStatus;
  processing_status: DocumentProcessingStatus;
  storage_key: string;
  created_at: string;
}

export const api = {
  auth: {
    me: () => request<UserProfile>('/api/v1/auth/me'),
  },
  documents: {
    upload: async (file: File): Promise<Document> => {
      const token = getStoredToken();
      const form = new FormData();
      form.append('file', file);

      let res: Response;
      try {
        res = await fetch(`${BASE}/api/v1/documents/upload`, {
          method: 'POST',
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: form,
        });
      } catch {
        // fetch() itself threw: the connection never completed (server down,
        // crashed mid-response, or a dev-server hot-reload killed it).
        throw new Error('Could not reach the server. Is the backend running?');
      }

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(extractErrorMessage(body, `Upload failed (${res.status})`));
      }
      return res.json() as Promise<Document>;
    },
  },
};
