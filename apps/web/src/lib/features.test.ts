import { describe, expect, it } from 'vitest';
import { NO_FEATURES, fetchFeatures, parseFeatures } from './features';

const json = (body: unknown, status = 200) => async () => new Response(JSON.stringify(body), { status });

describe('parseFeatures', () => {
  it('reads the three flags and only accepts literal true', () => {
    expect(parseFeatures({ diagram: true, videos: false, female_atlas: true })).toEqual({
      diagram: true,
      videos: false,
      female_atlas: true,
    });
    expect(parseFeatures({ diagram: 'true', videos: 1, female_atlas: null })).toEqual(NO_FEATURES);
  });
  it('treats non-objects as all false', () => {
    for (const bad of [null, undefined, [], 'x', 3, true]) expect(parseFeatures(bad)).toEqual(NO_FEATURES);
  });
  it('ignores unknown keys', () => {
    expect(parseFeatures({ ratelimit: true, other: true })).toEqual(NO_FEATURES);
  });
});

describe('fetchFeatures', () => {
  it('returns the flags on success and calls /api/features on the base URL', async () => {
    let seen = '';
    const fetchImpl = (async (u: string) => {
      seen = u;
      return new Response(JSON.stringify({ diagram: true, videos: false, female_atlas: false }));
    }) as unknown as typeof fetch;
    expect(await fetchFeatures({ baseUrl: 'http://api:8000/', fetchImpl })).toEqual({
      diagram: true,
      videos: false,
      female_atlas: false,
    });
    expect(seen).toBe('http://api:8000/api/features');
  });

  it('a failed fetch yields all flags false', async () => {
    const fetchImpl = (async () => {
      throw new Error('ECONNREFUSED');
    }) as unknown as typeof fetch;
    expect(await fetchFeatures({ baseUrl: 'http://x', fetchImpl })).toEqual(NO_FEATURES);
  });

  it('a non-2xx status or a bad body yields all flags false', async () => {
    expect(await fetchFeatures({ baseUrl: 'http://x', fetchImpl: json({ diagram: true }, 503) as unknown as typeof fetch })).toEqual(NO_FEATURES);
    const notJson = (async () => new Response('<html>', { status: 200 })) as unknown as typeof fetch;
    expect(await fetchFeatures({ baseUrl: 'http://x', fetchImpl: notJson })).toEqual(NO_FEATURES);
  });

  it('a timed-out fetch yields all flags false (aborted by the 1 s timer)', async () => {
    const hang = ((_u: string, init: RequestInit) =>
      new Promise((_res, rej) => {
        init.signal?.addEventListener('abort', () => rej(new DOMException('aborted', 'AbortError')));
      })) as unknown as typeof fetch;
    const t0 = Date.now();
    expect(await fetchFeatures({ baseUrl: 'http://x', fetchImpl: hang, timeoutMs: 30 })).toEqual(NO_FEATURES);
    expect(Date.now() - t0).toBeLessThan(1000);
  });
});
