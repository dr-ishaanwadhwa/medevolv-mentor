import { describe, expect, it } from 'vitest';
import type { Atlas } from './anatomy';
import { loadManifestFor, type ManifestDeps } from './atlas-store';

const manifest = (sex: 'male' | 'female' | undefined, version = 'v') =>
  ({ version, sex, parts: [], concepts: [], chunks: [], triangles: 0 }) as unknown as Atlas;

function deps(opts: { net?: unknown; netFails?: boolean; cache?: Record<string, Atlas> }) {
  const cache = { ...(opts.cache ?? {}) };
  const urls: string[] = [];
  const d: ManifestDeps = {
    fetchJson: async (url) => {
      urls.push(url);
      if (opts.netFails) throw new Error('offline');
      return opts.net;
    },
    getCached: async (key) => cache[key] ?? null,
    setCached: (key, data) => {
      cache[key] = data;
    },
  };
  return { d, cache, urls };
}

describe('loadManifestFor (F-1, F-1a)', () => {
  it('fetches the per-sex file and caches it under the per-sex key', async () => {
    const f = manifest('female');
    const { d, cache, urls } = deps({ net: f });
    await expect(loadManifestFor('female', d)).resolves.toBe(f);
    expect(urls[0]).toMatch(/female\.json$/);
    expect(cache['atlas.json:female']).toBe(f);
  });
  it('female fetch failure with only a cached male manifest stays an error (never male labelled female)', async () => {
    const { d } = deps({ netFails: true, cache: { 'atlas.json:male': manifest('male'), 'atlas.json': manifest('male') } });
    await expect(loadManifestFor('female', d)).rejects.toThrow();
  });
  it('female fetch failure falls back to the cached female manifest', async () => {
    const f = manifest('female', 'cached');
    const { d } = deps({ netFails: true, cache: { 'atlas.json:female': f } });
    await expect(loadManifestFor('female', d)).resolves.toBe(f);
  });
  it('a network answer of the wrong model is rejected', async () => {
    const { d } = deps({ net: manifest('male') });
    await expect(loadManifestFor('female', d)).rejects.toThrow(/female model/);
  });
  it('male falls back to its own key, then to the legacy single key, never to female', async () => {
    const legacy = manifest(undefined, 'legacy');
    await expect(loadManifestFor('male', deps({ netFails: true, cache: { 'atlas.json': legacy } }).d)).resolves.toBe(legacy);
    await expect(
      loadManifestFor('male', deps({ netFails: true, cache: { 'atlas.json:female': manifest('female') } }).d),
    ).rejects.toThrow();
  });
  it('male behaviour is unchanged with an older manifest without a sex field (F-6)', async () => {
    const m = manifest(undefined);
    const { d, urls } = deps({ net: m });
    await expect(loadManifestFor('male', d)).resolves.toBe(m);
    expect(urls[0]).toMatch(/atlas\.json$/);
  });
});
