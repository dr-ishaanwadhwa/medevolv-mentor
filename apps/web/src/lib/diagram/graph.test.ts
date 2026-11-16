import { describe, expect, it } from 'vitest';
import type { DiagramEdge, DiagramNode } from '../api';
import { citeLabel, citedSentenceCount, markersIn, maxPassageMarker, offersFlowchart, readingOrder, sentences, slugify, visibleSubgraph, wrapLabel } from './graph';

const A =
  'Beta blockers are classified into non-selective and cardioselective agents [1]. ' +
  'Non-selective beta blockers include propranolol [1]. Cardioselective ones include atenolol [2]. ' +
  'Propranolol must be avoided in asthma [G1].';
const cits = [{ index: 1 }, { index: 2 }];

describe('when the Flowchart chip shows (D-1, D-16)', () => {
  it('parses passage and fact markers like the server', () => {
    expect([...markersIn('x [1, 2] y [G3] z [G1, G2] [note]')].sort()).toEqual(['f1', 'f2', 'f3', 'p1', 'p2']);
  });
  it('joins a marker-only segment to the sentence before it', () => {
    expect(sentences('First fact. [1]\nSecond fact [2].')).toEqual(['First fact. [1]', 'Second fact [2].']);
  });
  it('lets list items inherit the marker of a cited lead-in, as the server does', () => {
    const sof =
      'The superior orbital fissure transmits [1]:\n\n- Trochlear nerve [IV]\n- Abducent nerve [VI]\n- Superior ophthalmic vein\n\nSee also [3].';
    expect(citedSentenceCount(sof, [1, 3])).toBe(5);
    expect(citedSentenceCount(sof.replace('transmits [1]:', 'transmits:'), [1, 3])).toBe(1);
    expect(sentences(sof)[1]).toBe('Trochlear nerve [IV] [1]');
  });
  it('counts only markers the answer really has', () => {
    expect(citedSentenceCount(A, [1, 2], [1])).toBe(4);
    expect(citedSentenceCount(A, [1], [])).toBe(2);
  });
  it('needs a signature, an answered status and 3 cited sentences', () => {
    const a = { text: A, status: 'answered', answer_sig: 'abc', citations: cits, graph_citations: [{ n: 1 }] };
    expect(offersFlowchart(a)).toBe(true);
    expect(offersFlowchart({ ...a, answer_sig: null })).toBe(false);
    expect(offersFlowchart({ ...a, answer_sig: undefined })).toBe(false);
    expect(offersFlowchart({ ...a, status: 'insufficient' })).toBe(false);
    expect(offersFlowchart({ ...a, status: 'personal_refusal' })).toBe(false);
    expect(offersFlowchart({ ...a, text: 'One [1]. Two [2].' })).toBe(false);
  });
  it('finds the highest passage marker', () => {
    expect(maxPassageMarker(A)).toBe(2);
  });
});

const n = (id: string, label = id): DiagramNode => ({ id, label, role: 'step', group: null, cites: [{ kind: 'passage', n: 1 }] });
const e = (from: string, to: string): DiagramEdge => ({ from, to, label: 'includes', cites: [{ kind: 'passage', n: 1 }] });
const NODES = ['r', 'a', 'b', 'a1', 'a2', 'b1'].map((x) => n(x));
const EDGES = [e('r', 'a'), e('r', 'b'), e('a', 'a1'), e('a', 'a2'), e('b', 'b1')];

describe('collapsible classification tree on phones', () => {
  it('shows the root and the first level, with hidden-children counts', () => {
    const v = visibleSubgraph(NODES, EDGES, new Set());
    expect(v.nodes.map((x) => x.id)).toEqual(['r', 'a', 'b']);
    expect(v.edges).toHaveLength(2);
    expect(Object.fromEntries(v.hiddenChildren)).toEqual({ a: 2, b: 1 });
  });
  it('opens one branch', () => {
    const v = visibleSubgraph(NODES, EDGES, new Set(['a']));
    expect(v.nodes.map((x) => x.id)).toEqual(['r', 'a', 'b', 'a1', 'a2']);
    expect(Object.fromEntries(v.hiddenChildren)).toEqual({ b: 1 });
  });
});

describe('helpers', () => {
  it('reads breadth-first from the roots', () => {
    expect(readingOrder(NODES, EDGES).map((x) => x.id)).toEqual(['r', 'a', 'b', 'a1', 'a2', 'b1']);
  });
  it('wraps at about 26 characters on word boundaries', () => {
    const lines = wrapLabel('Angiotensin converting enzyme inhibitors reduce aldosterone');
    expect(lines.every((l) => l.length <= 26)).toBe(true);
    expect(lines.join(' ')).toBe('Angiotensin converting enzyme inhibitors reduce aldosterone');
  });
  it('labels fact chips F (ontology) or G (the answer\'s own graph facts), passages by number', () => {
    expect(citeLabel({ kind: 'fact', n: 2 }, 'ontology')).toBe('F2');
    expect(citeLabel({ kind: 'fact', n: 1 }, 'answer')).toBe('G1');
    expect(citeLabel({ kind: 'passage', n: 3 }, 'answer')).toBe('3');
  });
  it('slugifies file names', () => {
    expect(slugify('Beta blockers: classification!')).toBe('beta-blockers-classification');
    expect(slugify(null)).toBe('diagram');
  });
});
