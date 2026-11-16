import { SYSTEMS, type Atlas, type Concept, type SystemId } from './anatomy';

/**
 * Grouped structure search. Results stay in rank order inside each group, and groups are ordered by their best
 * result, so the top hit is always first. A structure belongs to the body system most of its parts belong to.
 * Idea adapted from human-atlas-enhanced (MIT, see apps/web/THIRD_PARTY_NOTICES.md), which groups by body region;
 * our manifests carry systems, not regions, so systems are the grouping.
 */
export interface SearchGroup {
  system: SystemId;
  name: string;
  items: Concept[];
}

/** part id to system, built once per atlas. */
export function systemLookup(atlas: Pick<Atlas, 'parts'>): Map<string, SystemId> {
  return new Map(atlas.parts.map((p) => [p.id, p.system]));
}

/** The system most of a concept's parts belong to. Ties go to the system seen first. null when no part is known. */
export function conceptSystem(concept: Concept, bySystem: ReadonlyMap<string, SystemId>): SystemId | null {
  const counts = new Map<SystemId, number>();
  for (const id of concept.elements) {
    const s = bySystem.get(id);
    if (s) counts.set(s, (counts.get(s) ?? 0) + 1);
  }
  let best: SystemId | null = null;
  let top = 0;
  for (const [s, n] of counts) {
    if (n > top) {
      best = s;
      top = n;
    }
  }
  return best;
}

const systemName = (id: SystemId) => SYSTEMS.find((s) => s.id === id)?.name ?? id;

export function groupSearchResults(concepts: readonly Concept[], bySystem: ReadonlyMap<string, SystemId>): SearchGroup[] {
  const groups = new Map<SystemId, SearchGroup>();
  for (const c of concepts) {
    const system = conceptSystem(c, bySystem);
    if (!system) continue;
    let g = groups.get(system);
    if (!g) {
      g = { system, name: systemName(system), items: [] };
      groups.set(system, g);
    }
    g.items.push(c);
  }
  return [...groups.values()];
}

/** The results in the order they are listed (group by group), for arrow-key navigation. */
export const flattenGroups = (groups: readonly SearchGroup[]): Concept[] => groups.flatMap((g) => g.items);
