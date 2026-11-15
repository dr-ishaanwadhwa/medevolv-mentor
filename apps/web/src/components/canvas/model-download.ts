import { getCachedGeometryChunk, setCachedGeometryChunk } from '@/lib/idb';
import { modelUrl, type Atlas, type ChunkMeta } from '@/lib/anatomy';

/** Static hosts may serve .gz either as a gzip file or as Content-Encoding. fetch() already undoes the latter,
 * so inspect the payload signature to avoid decoding twice. */
async function decode(response: Response, expectedBytes: number, compressed: boolean): Promise<ArrayBuffer> {
  if (!response.ok) throw new Error('An anatomy file could not be loaded.');
  const payload = await response.arrayBuffer();
  const sig = new Uint8Array(payload, 0, Math.min(2, payload.byteLength));
  const gzip = compressed && sig[0] === 0x1f && sig[1] === 0x8b;
  const buffer = gzip
    ? await new Response(new Blob([payload]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer()
    : payload;
  if (buffer.byteLength !== expectedBytes) throw new Error('An anatomy file was incomplete. Please reload.');
  return buffer;
}

// Decoded chunks are shared between viewers (atlas page and concept-page embeds) for the page lifetime.
const memo = new Map<string, Promise<ArrayBuffer>>();

export function loadChunk(atlas: Atlas, chunk: ChunkMeta): Promise<ArrayBuffer> {
  const key = `${atlas.version}:${chunk.url}`;
  const hit = memo.get(key);
  if (hit) return hit;
  const p = (async () => {
    const cached = await getCachedGeometryChunk(key);
    if (cached && cached.byteLength === chunk.bytes) return cached;
    const compressed = !!chunk.gzip && typeof DecompressionStream !== 'undefined';
    const res = await fetch(modelUrl(compressed ? chunk.gzip! : chunk.url));
    const buffer = await decode(res, chunk.bytes, compressed);
    void setCachedGeometryChunk(key, buffer, chunk.bytes);
    return buffer;
  })();
  memo.set(key, p);
  // Failed or aborted downloads must not poison later attempts.
  p.catch(() => memo.delete(key));
  return p;
}
