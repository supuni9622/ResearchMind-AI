// Matches ErrorResponse/ErrorDetail in apps/api/app/schemas/common.py.
interface ApiErrorBody {
  error?: { code?: string; message?: string };
}

export function extractErrorMessage(body: unknown, fallback: string): string {
  return (body as ApiErrorBody)?.error?.message ?? fallback;
}
