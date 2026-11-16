/** Pure decisions for the landing stage (PRD 4.L Fallbacks, L-5, L-12). No DOM, no three.js: unit-tested in node. */

export type StageMode = 'live' | 'static';

export interface Env {
  webgl: boolean;
  /** navigator.connection?.saveData */
  saveData?: boolean;
  /** navigator.connection?.effectiveType */
  effectiveType?: string;
}

/** Why the page stays static, or null when the 3D stage may load. three.js is never imported when this is non-null. */
export function staticReason(env: Env): 'no-webgl' | 'save-data' | 'slow-connection' | null {
  if (!env.webgl) return 'no-webgl';
  if (env.saveData) return 'save-data';
  if (env.effectiveType === '2g' || env.effectiveType === 'slow-2g') return 'slow-connection';
  return null;
}

/** Time fallback: if library.bin has not decoded within this long of being requested, stay static (iOS has no
 * navigator.connection, so this is the only slow-network signal there). */
export const DATA_TIMEOUT_MS = 6000;

/** Honest caption for the map (L-12): the count is what is actually rendered. */
export function mapCaption(rendered: number, total: number): string {
  const fmt = (n: number) => n.toLocaleString('en-US');
  return rendered >= total
    ? `${fmt(total)} passages. Each dot is one.`
    : `Each dot is a passage. Showing ${fmt(rendered)} of ${fmt(total)} on this screen.`;
}

const smooth = (x: number, a: number, b: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/** What the canvas shows at story coordinate s (scene index + progress, 0..5). Scenes: 0 hero, 1 why, 2 decline,
 * 3 body, 4 more. `whyMix` blends the glowing books from the hero answer's to the Why verdict's. */
export interface SceneState {
  /** overall point brightness (decline dims it) */
  dim: number;
  /** how strongly the cited books stand out */
  focus: number;
  whyMix: number;
  /** point layer opacity (fades out behind the chiasm) */
  points: number;
  /** chiasm opacity */
  chiasm: number;
  /** book labels opacity */
  labels: number;
}

export function sceneState(s: number): SceneState {
  const decline = smooth(s, 1.55, 2.05) * (1 - smooth(s, 2.55, 2.95));
  const body = smooth(s, 2.45, 2.95) * (1 - smooth(s, 3.55, 3.95));
  return {
    dim: 1 - 0.78 * decline,
    focus: (1 - smooth(s, 1.5, 1.9)) * 0.95,
    whyMix: smooth(s, 0.55, 0.95),
    points: 1 - 0.82 * body - 0.3 * smooth(s, 3.6, 4.2),
    chiasm: body,
    labels: (1 - smooth(s, 1.55, 1.9)) + smooth(s, 3.7, 4.2) * 0.6,
  };
}

/** Reduced motion: no scroll-scrubbed blends, only the nearest scene's end state (the stage cross-fades to it). */
export function reducedSceneState(s: number): SceneState {
  const k = Math.min(4, Math.max(0, Math.round(s)));
  return sceneState(k === 0 ? 0 : k === 1 ? 1.05 : k);
}
