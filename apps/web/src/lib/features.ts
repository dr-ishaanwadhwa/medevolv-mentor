/** Runtime feature flags (PRD 5.6, D-9, D-15). Server-safe: no React, no `@/` imports.
 *
 * The root layout calls `fetchFeatures()` once per render on the server (1 s timeout, short revalidate) and hands the
 * result to `<FeaturesProvider>`. Components never call /api/features from the browser. Any failure, timeout, bad
 * status or non-object body means every flag is false, and only a literal JSON `true` turns a flag on. */

export const FEATURE_NAMES = ['diagram', 'videos', 'female_atlas'] as const;
export type FeatureName = (typeof FEATURE_NAMES)[number];
export type Features = Record<FeatureName, boolean>;

export const NO_FEATURES: Features = { diagram: false, videos: false, female_atlas: false };

export const FEATURES_TIMEOUT_MS = 1000;
/** Seconds the server may reuse a fetched answer: a flag flip shows up within about this long (plus one request). */
export const FEATURES_REVALIDATE_S = 5;

export function parseFeatures(body: unknown): Features {
  if (typeof body !== 'object' || body === null || Array.isArray(body)) return { ...NO_FEATURES };
  const src = body as Record<string, unknown>;
  return {
    diagram: src.diagram === true,
    videos: src.videos === true,
    female_atlas: src.female_atlas === true,
  };
}

export interface FetchFeaturesOptions {
  /** Defaults to BACKEND_API_URL (set on the v2-web container) or the local API. No trailing slash needed. */
  baseUrl?: string;
  timeoutMs?: number;
  /** Injected in tests. */
  fetchImpl?: typeof fetch;
}

export async function fetchFeatures(opts: FetchFeaturesOptions = {}): Promise<Features> {
  const base = (opts.baseUrl ?? process.env.BACKEND_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');
  const doFetch = opts.fetchImpl ?? fetch;
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), opts.timeoutMs ?? FEATURES_TIMEOUT_MS);
  try {
    const res = await doFetch(`${base}/api/features`, {
      signal: ctl.signal,
      // Next extends RequestInit with `next`; plain fetch ignores it.
      next: { revalidate: FEATURES_REVALIDATE_S },
    } as RequestInit);
    if (!res.ok) return { ...NO_FEATURES };
    return parseFeatures(await res.json());
  } catch {
    return { ...NO_FEATURES };
  } finally {
    clearTimeout(timer);
  }
}
