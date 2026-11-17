export type SystemId =
  | 'skeletal'
  | 'muscular'
  | 'cardiac'
  | 'sensory'
  | 'arterial'
  | 'venous'
  | 'nervous'
  | 'respiratory'
  | 'digestive'
  | 'urinary'
  | 'lymphatic'
  | 'endocrine'
  | 'reproductive'
  | 'reproductive_female'
  | 'pregnancy'
  | 'integumentary'
  | 'connective';

export interface SystemMeta {
  id: SystemId;
  name: string;
  color: string;
  description: string;
}

export const SYSTEMS: SystemMeta[] = [
  { id: 'skeletal', name: 'Skeleton', color: '#e2d9ba', description: 'Bones form the supporting framework of the body, protect organs, and provide attachment points for muscles.' },
  { id: 'muscular', name: 'Muscles', color: '#a85b50', description: 'Skeletal muscles generate movement by pulling on their attachments. Together with tendons, they move joints and stabilize posture.' },
  { id: 'cardiac', name: 'Heart', color: '#b96760', description: 'The heart is a muscular pump with four chambers. Its valves direct blood forward through pulmonary and systemic circuits.' },
  { id: 'sensory', name: 'Sensory organs', color: '#b0c8ce', description: 'Structures contributing to special senses including sight, hearing, and balance.' },
  { id: 'arterial', name: 'Arteries', color: '#c05245', description: 'Arteries carry oxygenated and systemic blood away from the heart to peripheral tissues.' },
  { id: 'venous', name: 'Veins', color: '#527c9f', description: 'Veins return deoxygenated blood from tissues toward the heart and pulmonary circulation.' },
  { id: 'nervous', name: 'Nervous system', color: '#d8b565', description: 'Brain, spinal cord, and peripheral nerves coordinating motor, sensory, and autonomic functions.' },
  { id: 'respiratory', name: 'Respiratory', color: '#b98991', description: 'Airways and lungs conducting gas exchange between alveolar air and capillary blood.' },
  { id: 'digestive', name: 'Digestive', color: '#b8916b', description: 'Gastrointestinal tract and accessory organs breaking down nutrients and absorbing water.' },
  { id: 'urinary', name: 'Urinary', color: '#b47961', description: 'Kidneys filtering blood, regulating electrolyte balance, and excreting waste via bladder.' },
  { id: 'lymphatic', name: 'Lymphatic', color: '#879f7c', description: 'Vessels and lymphoid tissue returning interstitial fluid and providing immune surveillance.' },
  { id: 'endocrine', name: 'Endocrine', color: '#c5a09a', description: 'Glandular organs secreting hormones regulating metabolism, growth, and homeostasis.' },
  { id: 'reproductive', name: 'Reproductive', color: '#bda098', description: 'Reproductive structures contributing to gametogenesis and sexual hormone production.' },
  { id: 'reproductive_female', name: 'Reproductive (female)', color: '#c98f9a', description: 'Uterus, uterine tubes, ovaries, vagina, supporting ligaments and the breast: structures of the female reproductive tract.' },
  { id: 'pregnancy', name: 'Pregnancy reference', color: '#d9a98c', description: 'Placenta and umbilical cord reference structures. Hidden by default; turn this layer on to see them.' },
  { id: 'integumentary', name: 'Body surface', color: '#ba9b7d', description: 'Skin providing an outer anatomical protective boundary and thermoregulation.' },
  { id: 'connective', name: 'Connective tissue', color: '#aec3bb', description: 'Cartilage, fascia, and ligaments stabilizing joints and transmitting structural tension.' },
];

export interface Part {
  id: string;
  name: string;
  conceptId: string;
  system: SystemId;
  chunk: number;
  positions: number;
  normals: number;
  indices: number;
  vertexCount: number;
  indexCount: number;
  bounds: [number[], number[]];
  /** Female study model only (ADR-003): native HRA female mesh or reshaped male BodyParts3D mesh. */
  origin?: 'hra-female' | 'bp3d-reshaped';
}

export interface Concept {
  id: string;
  name: string;
  elements: string[];
}

export interface ChunkMeta {
  url: string;
  bytes: number;
  gzip?: string;
  gzipBytes?: number;
}

export interface Atlas {
  version: string;
  sex?: 'male' | 'female';
  source?: string;
  scope?: string;
  parts: Part[];
  concepts: Concept[];
  chunks: ChunkMeta[];
  triangles: number;
}

export type View = 'three-quarter' | 'front' | 'back' | 'side' | 'anterior' | 'posterior' | 'lateral_left' | 'lateral_right' | 'superior' | 'isometric' | 'thoracic_left_oblique';

export interface SceneState {
  inspectorOpen?: boolean;
  explode: number;
  visible: SystemId[];
  selected: string[];
  isolate: boolean;
  view: View;
  rotate: boolean;
  reset: number;
}

export const DEFAULT_VISIBLE: SystemId[] = [
  'cardiac',
  'sensory',
  'skeletal',
  'muscular',
  'arterial',
  'venous',
  'nervous',
  'respiratory',
  'digestive',
  'urinary',
  'lymphatic',
  'endocrine',
  'reproductive',
  'reproductive_female',
  'connective',
];

export interface MereologyNode {
  fmaId: string;
  name: string;
  relation: string;
}

export interface CertifiedCondition {
  conditionId: string;
  name: string;
  relation: string;
  guidelineBadges?: string[];
}

export interface CitationPointer {
  book: string;
  edition: string;
  chapter: string;
  page: string;
  pointer: string;
  verifiedFact: string;
}

export interface ResolvedSpatialConcept {
  identifier: string;
  fmaId: string;
  canonicalName: string;
  latinName?: string;
  system: SystemId;
  meshPartIds: string[];
  boundingBox?: [[number, number, number], [number, number, number]];
  centroid?: [number, number, number];
  mereology?: {
    parents: MereologyNode[];
    children: MereologyNode[];
  };
  certifiedConditions?: CertifiedCondition[];
  citations?: CitationPointer[];
  socraticQuestions?: string[];
}

export type SpatialAction =
  | {
      type: 'spatial_action';
      action: 'highlight';
      conceptIds: string[];
      isolate?: boolean;
    }
  | {
      type: 'spatial_action';
      action: 'set_camera';
      preset: View;
      targetFmaId?: string;
      durationMs?: number;
    }
  | {
      type: 'spatial_action';
      action: 'dissect';
      visibleSystems?: SystemId[];
      peelSystems?: SystemId[];
    }
  | {
      type: 'spatial_action';
      action: 'reset';
    };

/* ---------------------------------------------------------------------------
 * Atlas helpers: model location, id resolution, and name search.
 * ------------------------------------------------------------------------- */

export const MODELS_BASE: string = (process.env.NEXT_PUBLIC_MODELS_BASE || '/models').replace(/\/$/, '');

/** atlas.json stores chunk urls as `/models/body-0.bin`; re-root them on MODELS_BASE. */
export function modelUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  return MODELS_BASE + '/' + path.replace(/^\/?models\//, '').replace(/^\//, '');
}

export interface AtlasIndex {
  partIndex: Map<string, number>;
  conceptById: Map<string, Concept>;
  partsByConcept: Map<string, number[]>;
}

export function buildIndex(atlas: Atlas): AtlasIndex {
  const partIndex = new Map<string, number>();
  atlas.parts.forEach((p, i) => partIndex.set(p.id, i));
  const conceptById = new Map<string, Concept>();
  atlas.concepts.forEach((c) => conceptById.set(c.id.toUpperCase(), c));
  const partsByConcept = new Map<string, number[]>();
  atlas.parts.forEach((p, i) => {
    const key = p.conceptId.toUpperCase();
    const list = partsByConcept.get(key);
    if (list) list.push(i);
    else partsByConcept.set(key, [i]);
  });
  return { partIndex, conceptById, partsByConcept };
}

export function normalizeFma(raw: string): string {
  const s = raw.trim().toUpperCase();
  return /^\d+$/.test(s) ? 'FMA' + s : s;
}

export interface HighlightResolution {
  partIdx: number[];
  matched: string[];
  unmatched: string[];
  names: string[];
}

/** Map FMA concept ids (or raw part ids) to part indexes in the atlas. */
export function resolveHighlight(atlas: Atlas, index: AtlasIndex, ids: string[]): HighlightResolution {
  const set = new Set<number>();
  const matched: string[] = [];
  const unmatched: string[] = [];
  const names: string[] = [];
  for (const raw of ids) {
    const id = normalizeFma(raw);
    if (!id) continue;
    const found = new Set<number>();
    const concept = index.conceptById.get(id);
    if (concept) {
      for (const e of concept.elements) {
        const i = index.partIndex.get(e);
        if (i !== undefined) found.add(i);
      }
    }
    index.partsByConcept.get(id)?.forEach((i) => found.add(i));
    const direct = index.partIndex.get(raw.trim()) ?? index.partIndex.get(id);
    if (direct !== undefined) found.add(direct);
    if (found.size) {
      found.forEach((i) => set.add(i));
      matched.push(id);
      names.push(concept?.name ?? atlas.parts[[...found][0]].name);
    } else unmatched.push(id);
  }
  return { partIdx: [...set].sort((a, b) => a - b), matched, unmatched, names };
}

export function conceptName(atlas: Atlas | null, index: AtlasIndex | null, id: string): string {
  if (!atlas || !index) return id;
  return index.conceptById.get(normalizeFma(id))?.name ?? id;
}

/** Name search over atlas concepts: exact > prefix > word-prefix > substring, shorter names first. */
export function searchStructures(atlas: Atlas, query: string, limit = 8): Concept[] {
  const q = query.toLowerCase().trim();
  if (q.length < 2) return [];
  const scored: [number, Concept][] = [];
  for (const c of atlas.concepts) {
    if (!c.elements.length) continue;
    const n = c.name.toLowerCase();
    let score = -1;
    if (n === q) score = 0;
    else if (n.startsWith(q)) score = 1;
    else if (n.includes(' ' + q)) score = 2;
    else if (n.includes(q)) score = 3;
    else if (c.id.toLowerCase() === q) score = 0;
    if (score >= 0) scored.push([score * 1000 + n.length, c]);
  }
  scored.sort((a, b) => a[0] - b[0]);
  return scored.slice(0, limit).map((x) => x[1]);
}

/** Quick-pick structures for the atlas empty state. */
export const SUGGESTED_STRUCTURES = ['heart', 'brain', 'liver', 'kidney', 'adrenal gland', 'optic chiasm', 'brachial plexus'];
