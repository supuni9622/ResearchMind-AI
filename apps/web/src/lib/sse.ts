// Minimal `text/event-stream` parser for `fetch`-based SSE consumption.
//
// The browser's native `EventSource` can't send a POST body or an
// `Authorization` header, and every streaming endpoint in this API is a
// POST that requires a bearer token — so streaming responses are read
// manually off the fetch `Response.body` instead.

export interface SSEEvent<T = unknown> {
  event: string;
  data: T;
}

export async function* parseSSEStream<T = unknown>(
  body: ReadableStream<Uint8Array>
): AsyncGenerator<SSEEvent<T>> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sepIndex = buffer.indexOf('\n\n');
      while (sepIndex !== -1) {
        const raw = buffer.slice(0, sepIndex);
        buffer = buffer.slice(sepIndex + 2);
        const parsed = parseEventBlock<T>(raw);
        if (parsed) yield parsed;
        sepIndex = buffer.indexOf('\n\n');
      }
    }
  } finally {
    reader.cancel().catch(() => {});
  }
}

function parseEventBlock<T>(raw: string): SSEEvent<T> | null {
  let eventType = 'message';
  const dataLines: string[] = [];

  for (const line of raw.split('\n')) {
    // Lines starting with ':' are comments — the streaming platform sends
    // `: ping` as a heartbeat to keep idle connections alive.
    if (line.startsWith(':') || line.length === 0) continue;
    if (line.startsWith('event:')) eventType = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
  }

  if (dataLines.length === 0) return null;

  try {
    return { event: eventType, data: JSON.parse(dataLines.join('\n')) as T };
  } catch {
    return null;
  }
}
