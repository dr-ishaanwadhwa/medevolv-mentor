'use client';
import { create } from 'zustand';
import { buildIndex, modelUrl, DEFAULT_VISIBLE, type Atlas, type AtlasIndex, type SystemId } from './anatomy';
import { getCachedManifest, setCachedManifest } from './idb';

interface AtlasState {
  atlas: Atlas | null;
  index: AtlasIndex | null;
  status: 'idle' | 'loading' | 'ready' | 'error';
  error: string;
  /** 0-100 geometry download progress for the full atlas viewer */
  progress: number;
  isolate: boolean;
  resetNonce: number;
  visible: SystemId[];
  loadManifest: () => Promise<void>;
  setProgress: (n: number) => void;
  setIsolate: (v: boolean) => void;
  reset: () => void;
  toggleSystem: (id: SystemId) => void;
  resetLayers: () => void;
}

let inflight: Promise<void> | null = null;

export const useAtlasStore = create<AtlasState>((set, get) => ({
  atlas: null,
  index: null,
  status: 'idle',
  error: '',
  progress: 0,
  isolate: false,
  resetNonce: 0,
  visible: DEFAULT_VISIBLE,
  loadManifest: () => {
    if (get().atlas) return Promise.resolve();
    if (inflight) return inflight;
    set({ status: 'loading', error: '' });
    inflight = (async () => {
      let atlas: Atlas | null = null;
      try {
        const r = await fetch(modelUrl('atlas.json'));
        if (!r.ok) throw new Error('The anatomy catalogue could not be loaded.');
        atlas = (await r.json()) as Atlas;
        void setCachedManifest('atlas.json', atlas);
      } catch (e) {
        atlas = await getCachedManifest<Atlas>('atlas.json');
        if (!atlas) {
          set({ status: 'error', error: e instanceof Error ? e.message : 'The anatomy catalogue could not be loaded.' });
          return;
        }
      }
      set({ atlas, index: buildIndex(atlas), status: 'ready' });
    })().finally(() => {
      inflight = null;
    });
    return inflight;
  },
  setProgress: (progress) => set({ progress }),
  setIsolate: (isolate) => set({ isolate }),
  reset: () => set((s) => ({ resetNonce: s.resetNonce + 1, isolate: false })),
  toggleSystem: (id) =>
    set((s) => ({ visible: s.visible.includes(id) ? s.visible.filter((x) => x !== id) : [...s.visible, id] })),
  resetLayers: () => set({ visible: DEFAULT_VISIBLE }),
}));
