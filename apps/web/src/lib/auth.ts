const COGNITO_DOMAIN =
  process.env.NEXT_PUBLIC_COGNITO_DOMAIN ??
  'https://us-east-19chs0pt6p.auth.us-east-1.amazoncognito.com';
const CLIENT_ID =
  process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? '1r4at7v1s9nr9jqots6gl15ht';
const REDIRECT_URI =
  process.env.NEXT_PUBLIC_REDIRECT_URI ?? 'http://localhost:3000/auth/callback';
const SCOPE = 'email openid phone';

export function buildLoginUrl(): string {
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: 'code',
    scope: SCOPE,
  });
  return `${COGNITO_DOMAIN}/login?${params}`;
}

export function buildLogoutUrl(baseUrl = 'http://localhost:3000'): string {
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    logout_uri: baseUrl,
  });
  return `${COGNITO_DOMAIN}/logout?${params}`;
}

export interface TokenResponse {
  id_token: string;
  access_token: string;
  refresh_token: string | null;
  token_type: string;
  expires_in: number;
}

export async function exchangeCode(code: string): Promise<TokenResponse> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
  const res = await fetch(`${apiUrl}/api/v1/auth/callback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, redirect_uri: REDIRECT_URI }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      (body as { detail?: string }).detail ?? `Authentication failed (${res.status})`
    );
  }

  return res.json() as Promise<TokenResponse>;
}

const TOKEN_KEY = 'rm_id_token';

export function storeToken(token: string): void {
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
  } catch {}
}

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function clearToken(): void {
  try {
    sessionStorage.removeItem(TOKEN_KEY);
  } catch {}
}
