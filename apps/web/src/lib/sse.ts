/** Minimal fetch-based SSE client (POST bodies, abortable, handles split chunks and multi-line data). */

export interface SSEMessage {
  event: string;
  data: string;
}

/** Parses an SSE byte stream into messages. Exported for tests. */
export async function* parseSSE(body: ReadableStream<Uint8Array>): AsyncGenerator<SSEMessage> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  try {
    for (;;) {
      const { value, done } = await reader.read();
      buf += decoder.decode(value, { stream: !done });
      buf = buf.replace(/\r\n?/g, '\n');
      let idx: number;
      while ((idx = buf.indexOf('\n\n')) !== -1) {
        const block = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const msg = parseBlock(block);
        if (msg) yield msg;
      }
      if (done) {
        const msg = parseBlock(buf);
        if (msg) yield msg;
        return;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseBlock(block: string): SSEMessage | null {
  let event = 'message';
  const data: string[] = [];
  for (const line of block.split('\n')) {
    if (!line || line.startsWith(':')) continue;
    const i = line.indexOf(':');
    const field = i === -1 ? line : line.slice(0, i);
    let val = i === -1 ? '' : line.slice(i + 1);
    if (val.startsWith(' ')) val = val.slice(1);
    if (field === 'event') event = val;
    else if (field === 'data') data.push(val);
  }
  return data.length ? { event, data: data.join('\n') } : null;
}

export interface StreamHandlers<E extends Record<string, unknown>> {
  /** Called for each named event with its JSON-parsed data. */
  onEvent: <K extends keyof E & string>(event: K, data: E[K]) => void;
  /** Network / HTTP / parse failure (not for server-sent `error` events; those arrive via onEvent). */
  onFail?: (err: Error) => void;
  onClose?: () => void;
}

export class HttpError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/** POST `body` as JSON and stream SSE events. Resolves when the stream ends or is aborted. */
export async function streamPost<E extends Record<string, unknown>>(
  url: string,
  body: unknown,
  handlers: StreamHandlers<E>,
  signal?: AbortSignal,
): Promise<void> {
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(body),
      signal,
      cache: 'no-store',
    });
    if (!res.ok || !res.body) {
      let detail = '';
      try {
        const j = await res.json();
        detail = typeof j?.detail === 'string' ? j.detail : '';
      } catch {
        /* non-JSON error body */
      }
      throw new HttpError(res.status, detail || `Request failed (${res.status})`);
    }
    for await (const m of parseSSE(res.body)) {
      let parsed: unknown;
      try {
        parsed = JSON.parse(m.data);
      } catch {
        continue; // ignore malformed event, keep stream alive
      }
      handlers.onEvent(m.event as keyof E & string, parsed as E[keyof E & string]);
    }
  } catch (e) {
    if ((e as Error).name === 'AbortError') return;
    handlers.onFail?.(e instanceof Error ? e : new Error(String(e)));
  } finally {
    handlers.onClose?.();
  }
}
