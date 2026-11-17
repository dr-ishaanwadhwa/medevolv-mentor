/** Typed fetchers for the concept / spatial endpoints, with small in-memory caches so Back is instant. */

export interface ConceptHit {
  id: string;
  label: string;
  type: string;
  degree: number;
}

export interface LinkRef {
  id: string;
  label: string;
  type: string;
  predicate?: string;
  tier: string;
}

export interface SectionRef {
  section_id: string;
  book_id: string;
  title: string;
  path: string;
  primary: boolean;
  tier?: string;
}

export interface ConceptPage {
  id: string;
  label: string;
  type: string;
  aliases: string[];
  books: string[];
  degree: number;
  sections: SectionRef[];
  links_out: LinkRef[];
  links_in: LinkRef[];
  links_out_total?: number;
  links_in_total?: number;
  hubs: { hub_id: string; label: string; type: string; tier: string }[];
  see_also: { id: string | null; label: string; score: number; books: string[]; section_id: string; tier: string }[];
  bodhi?: { bodhi_id: string; name: string; type: string; relation: string; tier: string }[];
  atlas: { link: string | null; structures: { label: string; atlas_name: string; url: string | null }[] };
  graph: {
    nodes: { id: string; label: string; type: string; center?: boolean }[];
    edges: { source: string; target: string; predicate: string; tier: string }[];
  };
}

export interface SpatialCitation {
  book: string;
  edition?: string;
  chapter?: string;
  pages?: string;
  section_id?: string;
  excerpt?: string | null;
}

export type SpatialOrigin = 'hra-female' | 'bp3d-reshaped' | 'mixed';

export interface SpatialResolve {
  fma_ids: string[];
  label: string;
  atlas: { label: string; atlas_name: string; fma_ids: string[]; url: string | null; sex?: 'male' | 'female'; origin?: SpatialOrigin | null }[];
  /** Female study model (ADR-003): what the female model draws for this structure. */
  origin?: SpatialOrigin | null;
  /** Model the structure belongs to; absent until the API ships the field. */
  sex?: 'male' | 'female';
  concept: { id: string; label: string; type: string; aliases: string[]; degree: number; books: string[] } | null;
  citations: SpatialCitation[];
  related: { id: string; label: string; type: string; shared_facts: number; tier: string }[];
  tier: 'navigation';
}

export class NotFoundError extends Error {}

const BOOKS: Record<string, string> = {
  tripathi: 'KD Tripathi, Pharmacology',
  guyton: 'Guyton & Hall, Physiology',
  robbins: 'Robbins, Pathology',
  davidson: 'Davidson, Medicine',
  micro: 'Microbiology',
  harrison: 'Harrison, Internal Medicine',
  grays: "Gray's Anatomy",
};
export const bookName = (id: string) => BOOKS[id] ?? id;

/** Path segment for a concept id (ids may contain "/" and ":"). */
export const conceptHref = (id: string) => `/c/${encodeURIComponent(id)}`;

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const r = await fetch(url, { signal });
  if (r.status === 404) throw new NotFoundError('Not found');
  if (!r.ok) throw new Error(`Request failed (${r.status})`);
  return (await r.json()) as T;
}

export function searchConcepts(q: string, signal?: AbortSignal, limit = 30): Promise<ConceptHit[]> {
  return getJson<ConceptHit[]>(`/api/concepts/search?q=${encodeURIComponent(q)}&limit=${limit}`, signal);
}

const conceptCache = new Map<string, ConceptPage>();
export const cachedConcept = (key: string) => conceptCache.get(key);

export async function fetchConcept(labelOrId: string, signal?: AbortSignal): Promise<ConceptPage> {
  const hit = conceptCache.get(labelOrId);
  if (hit) return hit;
  // ids contain "/", which FastAPI's path converter accepts when sent as-is.
  const page = await getJson<ConceptPage>(`/api/concepts/${encodeURIComponent(labelOrId).replace(/%2F/g, '/')}`, signal);
  conceptCache.set(labelOrId, page);
  conceptCache.set(page.id, page);
  return page;
}

const spatialCache = new Map<string, SpatialResolve>();

/** `sex` is the model the structure was tapped in. It is always sent, so the server can skip crosswalk rows drawn only
 * in the other model (a male tap never gets a female-only AtlasLink). */
export async function fetchSpatial(fma: string, signal?: AbortSignal, sex: 'male' | 'female' = 'male'): Promise<SpatialResolve> {
  const key = `${fma}|${sex}`;
  const hit = spatialCache.get(key);
  if (hit) return hit;
  const r = await getJson<SpatialResolve>(`/api/spatial/resolve?fma=${encodeURIComponent(fma)}&sex=${sex}`, signal);
  spatialCache.set(key, r);
  return r;
}

/** Colour per concept type (ontology semantic types), shared by pills and the graph. */
export const TYPE_META: Record<string, { label: string; color: string }> = {
  PathologicalCondition: { label: 'Condition', color: '#d4574e' },
  AnatomicalStructure: { label: 'Anatomy', color: '#2a9d8f' },
  ClinicalPhenotype: { label: 'Sign / symptom', color: '#e0a23a' },
  TherapeuticAgent: { label: 'Therapy', color: '#4f86d9' },
  DiagnosticModality: { label: 'Diagnostic', color: '#8a6fd1' },
  PhysiologicalProcess: { label: 'Physiology', color: '#3fae6a' },
  ClinicalStage: { label: 'Stage', color: '#b9783d' },
};
export function typeMeta(type: string) {
  return (
    TYPE_META[type] ?? {
      label: type.replace(/([a-z])([A-Z])/g, '$1 $2') || 'Concept',
      color: '#7a8a91',
    }
  );
}
