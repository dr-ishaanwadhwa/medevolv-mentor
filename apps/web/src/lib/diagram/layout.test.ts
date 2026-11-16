import { describe, expect, it } from 'vitest';
import type { DiagramEdge, DiagramNode } from '../api';
import { exportSvg, sourcePointers } from './export';
import { layoutDiagram } from './layout';

const n = (id: string, label: string, group: string | null = null, role: DiagramNode['role'] = 'step'): DiagramNode => ({
  id,
  label,
  role,
  group,
  cites: [{ kind: id === 'c' ? 'fact' : 'passage', n: 1 }],
});
const e = (from: string, to: string, label = ''): DiagramEdge => ({ from, to, label, cites: [{ kind: 'passage', n: 1 }] });

const seq = {
  kind: 'sequence' as const,
  nodes: [n('a', 'Angiotensin II', null, 'start'), n('b', 'Aldosterone release'), n('c', 'Sodium <reabsorption> & water', null, 'warning')],
  edges: [e('a', 'b', 'activates'), e('b', 'c', 'increases')],
  groups: [],
};

const overlap = (p: { x: number; y: number; w: number; h: number }, q: typeof p) =>
  p.x < q.x + q.w && q.x < p.x + p.w && p.y < q.y + q.h && q.y < p.y + p.h;

describe('dagre layout', () => {
  it('sequence runs top to bottom, inside the canvas, without overlapping boxes', () => {
    const l = layoutDiagram(seq);
    expect(l.rankdir).toBe('TB');
    const [a, b, c] = l.nodes;
    expect(a.y).toBeLessThan(b.y);
    expect(b.y).toBeLessThan(c.y);
    for (const x of l.nodes) {
      expect(x.x).toBeGreaterThanOrEqual(0);
      expect(x.y).toBeGreaterThanOrEqual(0);
      expect(x.x + x.w).toBeLessThanOrEqual(l.width);
      expect(x.y + x.h).toBeLessThanOrEqual(l.height);
    }
    expect(overlap(a, b) || overlap(b, c) || overlap(a, c)).toBe(false);
    expect(l.edges.every((x) => x.points.length >= 2)).toBe(true);
    expect(l.edges[0].lx).toBeTypeOf('number');
  });
  it('classification runs left to right', () => {
    const l = layoutDiagram({ ...seq, kind: 'classification', edges: [e('a', 'b'), e('a', 'c')] });
    expect(l.rankdir).toBe('LR');
    expect(l.nodes[0].x).toBeLessThan(l.nodes[1].x);
  });
  it('group bands enclose their member boxes', () => {
    const l = layoutDiagram({
      kind: 'case',
      nodes: [n('a', 'Condition', null, 'start'), n('b', 'Fever', 'g1'), n('c', 'Rash', 'g1')],
      edges: [e('a', 'b'), e('a', 'c')],
      groups: [{ id: 'g1', title: 'Presentation' }, { id: 'g2', title: 'Unused' }],
    });
    expect(l.groups.map((g) => g.id)).toEqual(['g1']);
    const g = l.groups[0];
    for (const x of l.nodes.filter((m) => m.group === 'g1')) {
      expect(x.x).toBeGreaterThan(g.x);
      expect(x.x + x.w).toBeLessThan(g.x + g.w);
      expect(x.y).toBeGreaterThan(g.y);
    }
  });
});

describe('export (D-7)', () => {
  it('white background, escaped labels, study-aid line and pointer-only sources', () => {
    const l = layoutDiagram(seq);
    const pointers = sourcePointers(
      l,
      'answer',
      [{ index: 1, book: 'Guyton', edition: '14', chapter: 'Renal', pages: '402' }],
      [{ n: 1, fact_id: 'g-1', book: 'KDT', edition: '', chapter: '', pages: '' }],
    );
    expect(pointers).toEqual(['[1] Guyton 14e, Renal, p 402', '[G1] KDT']);
    const { svg, width, height } = exportSvg(l, { title: 'RAAS', source: 'answer', pointers, date: new Date('2026-11-16T00:00:00Z') });
    expect(svg).toContain('<rect width="100%" height="100%" fill="#ffffff"/>');
    expect(svg).toContain('Sodium &lt;reabsorption&gt; &amp;');
    expect(svg).not.toContain('<reabsorption>');
    expect(svg).toContain('Study aid summarised from textbooks. Not for decisions about a real patient.');
    expect(svg).toContain('[1] Guyton 14e, Renal, p 402');
    expect(svg).toContain('2026-11-16');
    expect(width).toBeGreaterThanOrEqual(l.width);
    expect(height).toBeGreaterThan(l.height);
  });
});
