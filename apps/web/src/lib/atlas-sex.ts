/** Pure logic for the Male | Female (study model) atlas switch (PRD 4.5, D-8). No React, no `@/` imports, so Node tests run it.
 *
 * One model is in the scene at a time; the two are never overlaid or morphed. Selection is carried across by concept
 * id, never by part index. Everything here is gated by the `female_atlas` flag at the call sites: with the flag off
 * the caller passes `flag: false` and only the male model is ever reachable. */
import { buildIndex, resolveHighlight, type Atlas, type AtlasIndex } from './anatomy';

export type Sex = 'male' | 'female';
export const SEXES: readonly Sex[] = ['male', 'female'];

/** One sentence under the toggle while the female model is shown (ADR-003: the study model is male-derived). */
export const FEMALE_NOTE =
  'Female study model: a male body reshaped to a female form, with female organs from the Human Reference Atlas; for orientation only.';

// ---------------------------------------------------------------- native vs reshaped parts (ADR-003)

/** Where a part's geometry comes from. `hra-female`: Human Reference Atlas female data. `bp3d-reshaped`: a male
 * BodyParts3D mesh reshaped to a female form by the study model's morph fields. Male-model parts have no origin. */
export type PartOrigin = 'hra-female' | 'bp3d-reshaped';
export type SelectionOrigin = PartOrigin | 'mixed';

/** Origin of what a concept id draws in this model: one origin, 'mixed', or null (not drawn, or no origin data). */
export function originOf(atlas: Atlas | null, index: AtlasIndex | null, id: string): SelectionOrigin | null {
  if (!atlas || !index) return null;
  const seen = new Set<PartOrigin>();
  for (const i of resolveHighlight(atlas, index, [id]).partIdx) {
    const o = atlas.parts[i].origin;
    if (!o) return null;
    seen.add(o);
  }
  if (seen.size === 0) return null;
  return seen.size > 1 ? 'mixed' : [...seen][0];
}

/** Short line for the selection panel. Reshaped parts must never read as female anatomy data. */
export function originLabel(o: SelectionOrigin): string {
  if (o === 'bp3d-reshaped') return 'Reshaped from the male model (BodyParts3D), not female anatomy data.';
  if (o === 'hra-female') return 'Female anatomy data from the Human Reference Atlas, fitted into this body.';
  return 'Partly reshaped from the male model, partly female anatomy data from the Human Reference Atlas.';
}

export function parseSex(raw: string | null | undefined): Sex | null {
  const v = (raw ?? '').trim().toLowerCase();
  return v === 'female' || v === 'male' ? v : null;
}

export const otherSex = (s: Sex): Sex => (s === 'male' ? 'female' : 'male');
/** Labels of the Male | Female switch. The female set is the male-derived study model (ADR-003), so it says so. */
export const SEX_TOGGLE_LABEL: Record<Sex, string> = { male: 'Male', female: 'Female (study model)' };
export const sexLabel = (s: Sex): string => (s === 'male' ? 'Male' : 'Female');

/** Manifest file under the models base. */
export const manifestFile = (s: Sex): string => (s === 'female' ? 'female.json' : 'atlas.json');

/** IndexedDB manifest key, per sex (F-1a): a failed female fetch must never fall back to the male manifest. */
export const manifestCacheKey = (s: Sex): string => `atlas.json:${s}`;
/** Before per-sex keys the male manifest was cached under this key; only the male model may fall back to it. */
export const LEGACY_MALE_CACHE_KEY = 'atlas.json';

/** A manifest must be the model it was asked for. The male file predates the `sex` field in older builds. */
export function manifestMatches(sex: Sex, atlas: Pick<Atlas, 'sex' | 'parts' | 'concepts' | 'chunks'> | null | undefined): boolean {
  if (!atlas || !Array.isArray(atlas.parts) || !Array.isArray(atlas.concepts) || !Array.isArray(atlas.chunks)) return false;
  if (sex === 'female') return atlas.sex === 'female';
  return atlas.sex !== 'female';
}

// ---------------------------------------------------------------- URL

/** Set or remove `sex`, keeping every other query param (`select`, ...). Returns "?a=b" or "". */
export function withSex(search: string, sex: Sex | null): string {
  const p = new URLSearchParams(search);
  p.delete('sex');
  if (sex) p.set('sex', sex);
  // keep `select` readable: commas are not percent-encoded
  const q = p
    .toString()
    .replace(/%2C/gi, ',');
  return q ? `?${q}` : '';
}

/** Set sex and replace `select` in one step (a model switch changes both). */
export function withSexAndSelection(search: string, sex: Sex | null, select: string[]): string {
  const p = new URLSearchParams(search);
  p.delete('sex');
  p.delete('select');
  const rest = p.toString().replace(/%2C/gi, ',');
  const parts = [
    select.length ? `select=${select.map(encodeURIComponent).join(',')}` : '',
    sex ? `sex=${sex}` : '',
    rest,
  ].filter(Boolean);
  return parts.length ? `?${parts.join('&')}` : '';
}

export interface UrlDecision {
  /** the model the URL asks for (after flag gating) */
  target: Sex;
  /** the URL carries a `sex` param that must be removed (flag off: ignore it silently) */
  stripParam: boolean;
  /** stored preference applies (no `sex`, no `select`, flag on) */
  fromStored: boolean;
}

/**
 * Which model the URL asks for.
 * - flag off: always male, and a `sex` param is stripped (no toast).
 * - `?sex=` wins; a `?select=` link wins over the stored preference; the stored preference only applies to a bare URL.
 */
export function decideTarget(opts: { param: string | null; hasSelect: boolean; flag: boolean; stored: Sex | null }): UrlDecision {
  const { param, hasSelect, flag, stored } = opts;
  if (!flag) return { target: 'male', stripParam: param !== null, fromStored: false };
  const p = parseSex(param);
  if (p) return { target: p, stripParam: false, fromStored: false };
  if (!hasSelect && stored) return { target: stored, stripParam: false, fromStored: true };
  return { target: 'male', stripParam: false, fromStored: false };
}

// ---------------------------------------------------------------- selection across models

export function hasConcept(atlas: Atlas | null, index: AtlasIndex | null, id: string): boolean {
  if (!atlas || !index) return false;
  return resolveHighlight(atlas, index, [id]).matched.length > 0;
}

export interface Partition {
  keep: string[];
  dropped: string[];
}

/** Ids that exist in the target model are kept (by concept id), the rest are dropped. */
export function partitionSelection(ids: readonly string[], atlas: Atlas | null, index: AtlasIndex | null): Partition {
  const keep: string[] = [];
  const dropped: string[] = [];
  for (const id of ids) (hasConcept(atlas, index, id) ? keep : dropped).push(id);
  return { keep, dropped };
}

/**
 * Symmetric auto-switch: when every selected id is missing from the loaded model and at least one is present in the
 * other, return the other sex. Returns null otherwise (nothing selected, found in the current model, or in neither).
 * `other` may be null when its manifest is not loaded: the caller loads it first.
 */
export function autoSwitchTarget(
  current: Sex,
  ids: readonly string[],
  cur: { atlas: Atlas | null; index: AtlasIndex | null },
  other: { atlas: Atlas | null; index: AtlasIndex | null } | null,
): Sex | null {
  if (!ids.length || !cur.atlas || !cur.index) return null;
  if (ids.some((id) => hasConcept(cur.atlas, cur.index, id))) return null;
  if (!other || !other.atlas) return null;
  return ids.some((id) => hasConcept(other.atlas, other.index, id)) ? otherSex(current) : null;
}

// ---------------------------------------------------------------- default view per model

const PELVIC_BONE = /\b(ilium|ischium|pubis|sacrum|coccyx)\b/i;

/**
 * Part indices the default view of a model frames. `null` means the whole visible body (the male default, D-4).
 * Female: the torso and pelvis, i.e. Reproductive (female), Urinary and the pelvic bones; the pregnancy reference
 * parts are hidden by default and never enlarge the frame.
 */
export function defaultFramingParts(atlas: Atlas, sex: Sex): number[] | null {
  if (sex !== 'female') return null;
  const idx: number[] = [];
  atlas.parts.forEach((p, i) => {
    if (p.system === 'reproductive_female' || p.system === 'urinary') idx.push(i);
    else if (p.system === 'skeletal' && PELVIC_BONE.test(p.name)) idx.push(i);
  });
  return idx.length ? idx : null;
}

// ---------------------------------------------------------------- download size and progress

export function gzipTotalBytes(atlas: Pick<Atlas, 'chunks'> | null): number {
  if (!atlas) return 0;
  return atlas.chunks.reduce((n, c) => n + (c.gzipBytes ?? c.bytes), 0);
}

export const megabytes = (bytes: number): number => Math.round(bytes / 1_000_000);

/** "12 of 30 MB" for aria-valuetext. */
export function progressText(pct: number, totalBytes: number): string {
  const total = megabytes(totalBytes);
  const done = Math.min(total, Math.round((total * Math.max(0, Math.min(100, pct))) / 100));
  return `${done} of ${total} MB`;
}

/** Milestone announcements only (25 / 50 / 75), never per chunk. Returns the milestone crossed going prev -> next. */
export function milestoneCrossed(prev: number, next: number): 25 | 50 | 75 | null {
  for (const m of [75, 50, 25] as const) if (prev < m && next >= m) return m;
  return null;
}

/** Save-Data or a 2g/3g connection: "Not now" is the focused default of the confirm sheet. */
export function isConstrainedConnection(
  conn: { saveData?: boolean; effectiveType?: string } | null | undefined,
): boolean {
  if (!conn) return false;
  return !!conn.saveData || /^(slow-2g|2g|3g)$/.test(conn.effectiveType ?? '');
}

// ---------------------------------------------------------------- per-browser convenience (localStorage)

const PREF_KEY = 'medevolv.atlas.sex';
const CONFIRM_KEY = 'medevolv.atlas.femaleConfirmed';

type Store = Pick<Storage, 'getItem' | 'setItem'>;
const ls = (): Store | null => {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage;
  } catch {
    return null;
  }
};

export function readSexPreference(store: Store | null = ls()): Sex | null {
  try {
    return parseSex(store?.getItem(PREF_KEY));
  } catch {
    return null;
  }
}
export function writeSexPreference(sex: Sex, store: Store | null = ls()): void {
  try {
    store?.setItem(PREF_KEY, sex);
  } catch {
    /* private mode: the preference is only a convenience */
  }
}
/** True once the student confirmed the first female download in this browser. */
export function readFemaleConfirmed(store: Store | null = ls()): boolean {
  try {
    return store?.getItem(CONFIRM_KEY) === '1';
  } catch {
    return false;
  }
}
export function writeFemaleConfirmed(store: Store | null = ls()): void {
  try {
    store?.setItem(CONFIRM_KEY, '1');
  } catch {
    /* ignore */
  }
}

/** Convenience for tests and callers that hold only a manifest. */
export function indexOf(atlas: Atlas | null): AtlasIndex | null {
  return atlas ? buildIndex(atlas) : null;
}
