import { describe, expect, it } from 'vitest';
import type { Concept, SystemId } from './anatomy';
import { conceptSystem, flattenGroups, groupSearchResults } from './atlas-search';

const bySystem = new Map<string, SystemId>([
  ['p1', 'skeletal'],
  ['p2', 'skeletal'],
  ['p3', 'muscular'],
  ['p4', 'cardiac'],
  ['p5', 'muscular'],
]);
const c = (id: string, ...elements: string[]): Concept => ({ id, name: id, elements });

describe('conceptSystem', () => {
  it('uses the system most of the parts belong to', () => {
    expect(conceptSystem(c('a', 'p1', 'p3', 'p5'), bySystem)).toBe('muscular');
  });
  it('breaks ties by first appearance and ignores unknown parts', () => {
    expect(conceptSystem(c('a', 'p3', 'p1'), bySystem)).toBe('muscular');
    expect(conceptSystem(c('a', 'zzz', 'p4'), bySystem)).toBe('cardiac');
    expect(conceptSystem(c('a', 'zzz'), bySystem)).toBeNull();
  });
});

describe('groupSearchResults', () => {
  const ranked = [c('r1', 'p3'), c('r2', 'p1'), c('r3', 'p5'), c('r4', 'p4'), c('r5', 'p2')];
  it('groups by system, keeping rank order inside a group', () => {
    const g = groupSearchResults(ranked, bySystem);
    expect(g.map((x) => x.system)).toEqual(['muscular', 'skeletal', 'cardiac']);
    expect(g[0].items.map((x) => x.id)).toEqual(['r1', 'r3']);
    expect(g[1].items.map((x) => x.id)).toEqual(['r2', 'r5']);
  });
  it('orders groups by their best result, so the top hit is always first', () => {
    expect(flattenGroups(groupSearchResults(ranked, bySystem))[0].id).toBe('r1');
  });
  it('gives groups a readable name and drops concepts with no known system', () => {
    const g = groupSearchResults([c('x', 'nope'), c('r1', 'p3')], bySystem);
    expect(g).toHaveLength(1);
    expect(g[0].name).toBe('Muscles');
  });
  it('flattens in listed order for arrow-key navigation', () => {
    expect(flattenGroups(groupSearchResults(ranked, bySystem)).map((x) => x.id)).toEqual(['r1', 'r3', 'r2', 'r5', 'r4']);
  });
  it('returns nothing for no results', () => {
    expect(groupSearchResults([], bySystem)).toEqual([]);
  });
});
