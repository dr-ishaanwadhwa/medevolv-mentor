'use client';
import { create } from 'zustand';
import { buildIndex, modelUrl, DEFAULT_VISIBLE, type Atlas, type AtlasIndex, type SystemId } from './anatomy';
import { getCachedManifest, setCachedManifest } from './idb';
import { hideParts, revealParts } from './atlas-hidden';
import { LEGACY_MALE_CACHE_KEY, manifestCacheKey, manifestFile, manifestMatches, type Sex } from './atlas-sex';

type Status = 'idle' | 'loading' | 'ready' | 'error';
const both = <T,>(m: T, f: T): Record<Sex, T> => ({ male: m, female: f });

interface AtlasState {
  /** One manifest per model (F-1). Never merged, never mixed in one scene. */
  atlases: Record<Sex, Atlas | null>;
  indexes: Record<Sex, AtlasIndex | null>;
  statuses: Record<Sex, Status>;
  errors: Record<Sex, string>;
  /** 0-100 geometry download progress for the full atlas viewer (the model currently in the scene) */
  progress: number;
  /** Which model `progress` belongs to (so a stale 100 from the other model is never read as this one's) */
  progressSex: Sex | null;
  /** The model whose geometry is fully in the full viewer's scene, or null while loading */
  modelReady: Sex | null;
  /** The full viewer failed to load a model's geometry (the toolbar then falls back to Male) */
  sceneError: { sex: Sex; message: string } | null;
  isolate: boolean;
  /** Part ids hidden with the Hide control, for the model in the scene. Cleared by Reset view and by a model switch. */
  hiddenParts: string[];
  /** Explode amount: 0 assembled, 0.3 systems apart, 1 every piece. */
  explode: number;
  resetNonce: number;
  visible: SystemId[];
  loadManifest: (sex?: Sex) => Promise<void>;
  setProgress: (n: number, sex?: Sex) => void;
  setModelReady: (s: Sex | null) => void;
  setSceneError: (e: { sex: Sex; message: string } | null) => void;
  setIsolate: (v: boolean) => void;
  hideParts: (ids: string[]) => void;
  revealParts: (ids: string[]) => void;
  setHiddenParts: (ids: string[]) => void;
  setExplode: (n: number) => void;
  reset: () => void;
  toggleSystem: (id: SystemId) => void;
  resetLayers: () => void;
}

export interface ManifestDeps {
  fetchJson: (url: string) => Promise<unknown>;
  getCached: (key: string) => Promise<Atlas | null>;
  setCached: (key: string, data: Atlas) => void;
}

const CATALOGUE_ERROR = (sex: Sex) =>
  sex === 'female' ? "Couldn't load the female model." : 'The anatomy catalogue could not be loaded.';

/**
 * Fetch one model's manifest. The network answer must be that model's manifest. On a fetch failure only the same
 * model's cache may answer (F-1a); the female model never falls back to the male manifest (or the reverse), so the
 * UI can never show one model while labelled as the other. Throws when nothing valid is available.
 */
export async function loadManifestFor(sex: Sex, deps: ManifestDeps): Promise<Atlas> {
  const key = manifestCacheKey(sex);
  try {
    const body = await deps.fetchJson(modelUrl(manifestFile(sex)));
    if (!manifestMatches(sex, body as Atlas)) throw new Error(CATALOGUE_ERROR(sex));
    deps.setCached(key, body as Atlas);
    return body as Atlas;
  } catch (e) {
    let cached = await deps.getCached(key);
    if (!cached && sex === 'male') cached = await deps.getCached(LEGACY_MALE_CACHE_KEY);
    if (cached && manifestMatches(sex, cached)) return cached;
    throw e instanceof Error ? e : new Error(CATALOGUE_ERROR(sex));
  }
}

const browserDeps: ManifestDeps = {
  fetchJson: async (url) => {
    const r = await fetch(url);
    if (!r.ok) throw new Error('The anatomy catalogue could not be loaded.');
    return r.json();
  },
  getCached: (key) => getCachedManifest<Atlas>(key),
  setCached: (key, data) => void setCachedManifest(key, data),
};

const inflight: Partial<Record<Sex, Promise<void>>> = {};

export const useAtlasStore = create<AtlasState>((set, get) => ({
  atlases: both(null, null),
  indexes: both(null, null),
  statuses: both<Status>('idle', 'idle'),
  errors: both('', ''),
  progress: 0,
  progressSex: null,
  modelReady: null,
  sceneError: null,
  isolate: false,
  hiddenParts: [],
  explode: 0,
  resetNonce: 0,
  visible: DEFAULT_VISIBLE,
  loadManifest: (sex = 'male') => {
    if (get().atlases[sex]) return Promise.resolve();
    const running = inflight[sex];
    if (running) return running;
    set((s) => ({ statuses: { ...s.statuses, [sex]: 'loading' }, errors: { ...s.errors, [sex]: '' } }));
    const p = (async () => {
      try {
        const atlas = await loadManifestFor(sex, browserDeps);
        set((s) => ({
          atlases: { ...s.atlases, [sex]: atlas },
          indexes: { ...s.indexes, [sex]: buildIndex(atlas) },
          statuses: { ...s.statuses, [sex]: 'ready' },
        }));
      } catch (e) {
        set((s) => ({
          statuses: { ...s.statuses, [sex]: 'error' },
          errors: { ...s.errors, [sex]: e instanceof Error ? e.message : CATALOGUE_ERROR(sex) },
        }));
      }
    })().finally(() => {
      delete inflight[sex];
    });
    inflight[sex] = p;
    return p;
  },
  setProgress: (progress, sex) => set((s) => ({ progress, progressSex: sex ?? s.progressSex })),
  setModelReady: (modelReady) => set({ modelReady }),
  setSceneError: (sceneError) => set({ sceneError }),
  setIsolate: (isolate) => set({ isolate }),
  hideParts: (ids) => set((s) => ({ hiddenParts: hideParts(s.hiddenParts, ids) })),
  revealParts: (ids) => set((s) => (s.hiddenParts.some((h) => ids.includes(h)) ? { hiddenParts: revealParts(s.hiddenParts, ids) } : s)),
  setHiddenParts: (hiddenParts) => set({ hiddenParts: [...hiddenParts] }),
  setExplode: (n) => set({ explode: Math.max(0, Math.min(1, Number.isFinite(n) ? n : 0)) }),
  reset: () => set((s) => ({ resetNonce: s.resetNonce + 1, isolate: false, hiddenParts: [], explode: 0 })),
  toggleSystem: (id) =>
    set((s) => ({ visible: s.visible.includes(id) ? s.visible.filter((x) => x !== id) : [...s.visible, id] })),
  resetLayers: () => set({ visible: DEFAULT_VISIBLE }),
}));
