/**
 * Pure flowchart helpers (PRD 4.1): when to offer the chip, label wrapping, collapsing classification trees on
 * phones, the screen-reader reading order. No React and no `@/` imports, so the unit runner loads it directly.
 */
import type { DiagramEdge, DiagramNode } from '../api';

/** Statuses that never offer the Flowchart chip (D-1). */
export const NO_FLOWCHART_STATUSES = ['not_in_sources', 'insufficient', 'personal_refusal'] as const;
export const MIN_CITED_SENTENCES = 3;

const MARK = /\[([^[\]]{1,40})\]/g;
const MARK_BODY = /^\s*G?\d+(?:\s*,\s*G?\d+)*\s*$/i;

/** Passage ([n]) and fact ([G#]) markers in a text, as "p1" / "f1" keys. Mirrors api/diagram_validate.markers_in. */
export function markersIn(text: string): Set<string> {
  const out = new Set<string>();
  for (const m of text.matchAll(MARK)) {
    const body = m[1];
    if (!MARK_BODY.test(body)) continue;
    const toks = body.split(',').map((t) => t.trim());
    const fact = /^g/i.test(toks[0]);
    for (const t of toks) out.add(`${fact || /^g/i.test(t) ? 'f' : 'p'}${parseInt(t.replace(/^g/i, ''), 10)}`);
  }
  return out;
}

/** Removes citation markers only ("[VII]" or "[V1]" is answer text), as api/diagram_validate.strip_markers. */
const CITE = /\[\s*G?\d+(?:\s*,\s*G?\d+)*\s*\]/gi;
const stripMarkers = (s: string) => s.replace(CITE, ' ').replace(/\s+/g, ' ').trim();
const ITEM = /^(\s*)(?:[*\-•+]+|\d+[.)])\s+/;
const HEADING = /^\s*(?:#{1,6}\s+[^\n]{1,80}|\*\*[^*\n]{1,80}\*\*\s*:?)\s*$/;
const SPLIT = /(?<=[.!?])\s+(?=[A-Z[(*\-•\d])/;

/**
 * Answer sentences, each with its markers, as api/diagram_validate.sentences: a marker-only segment joins the sentence
 * before it, and a list item with no marker of its own carries the markers of the cited line that introduces the list
 * ("The superior orbital fissure transmits [1]:" or a parent bullet ending in ":"). A plain paragraph line ends the list.
 */
export function sentences(answer: string): string[] {
  const out: string[] = [];
  let leadMarks = '';
  let sub = null as { indent: number; marks: string } | null;
  const emit = (body: string, inherit: string) => {
    for (const raw of body.split(SPLIT)) {
      const p = raw.trim().replace(/^\s*(?:[*\-•>#]+|\d+[.)])\s+/, '');
      if (!p) continue;
      if (out.length && !stripMarkers(p).replace(/[ .,;:*-]/g, '')) out[out.length - 1] += ` ${p}`;
      else out.push(inherit ? `${p} ${inherit}` : p);
    }
  };
  for (const line of answer.replace(/\r\n?/g, '\n').split('\n')) {
    if (!line.trim()) continue;
    const m = ITEM.exec(line);
    if (m) {
      const indent = m[1].replace(/\t/g, '    ').length;
      const body = line.slice(m[0].length).trim();
      if (sub && indent <= sub.indent) sub = null;
      const inherit: string = markersIn(body).size ? '' : sub?.marks || leadMarks;
      emit(body, inherit);
      if (stripMarkers(body).endsWith(':')) sub = { indent, marks: (body.match(CITE) ?? []).join(' ') || inherit };
      continue;
    }
    if (HEADING.test(line) && !markersIn(line).size) {
      sub = null;
      emit(line.trim(), '');
      continue;
    }
    sub = null;
    leadMarks = stripMarkers(line).endsWith(':') ? (line.match(CITE) ?? []).join(' ') : '';
    emit(line.trim(), '');
  }
  return out;
}

/** Sentences that carry at least one marker the answer really has (passage index or graph fact number). */
export function citedSentenceCount(answer: string, passageNs: number[], factNs: number[] = []): number {
  const ok = new Set([...passageNs.map((n) => `p${n}`), ...factNs.map((n) => `f${n}`)]);
  return sentences(answer).filter((s) => [...markersIn(s)].some((m) => ok.has(m))).length;
}

/** The chip shows only for signed, answered, non-patient answers with at least 3 cited sentences (D-1, D-16). */
export function offersFlowchart(a: {
  text: string;
  status: string;
  answer_sig?: string | null;
  citations: { index: number }[];
  graph_citations?: { n: number }[];
}): boolean {
  if (!a.answer_sig) return false;
  if ((NO_FLOWCHART_STATUSES as readonly string[]).includes(a.status)) return false;
  const passages = a.citations.map((c) => c.index);
  const facts = (a.graph_citations ?? []).map((g) => g.n);
  return citedSentenceCount(a.text, passages, facts) >= MIN_CITED_SENTENCES;
}

/** Highest passage marker in the text, for "Drawing a flowchart from citations [1]-[k]". */
export function maxPassageMarker(answer: string): number {
  let k = 0;
  for (const m of markersIn(answer)) if (m.startsWith('p')) k = Math.max(k, parseInt(m.slice(1), 10));
  return k;
}

/** Wraps a label at about `width` characters on word boundaries (same width as `_wrap` in rag/diagrams.py). */
export function wrapLabel(label: string, width = 26): string[] {
  const words = label.trim().split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let cur = '';
  for (const w of words) {
    if (!cur) cur = w;
    else if ((cur + ' ' + w).length <= width) cur += ' ' + w;
    else {
      lines.push(cur);
      cur = w;
    }
  }
  if (cur) lines.push(cur);
  return lines.length ? lines : [''];
}

function childrenOf(edges: DiagramEdge[]): Map<string, string[]> {
  const m = new Map<string, string[]>();
  for (const e of edges) m.set(e.from, [...(m.get(e.from) ?? []), e.to]);
  return m;
}

function roots(nodes: DiagramNode[], edges: DiagramEdge[]): string[] {
  const hasIn = new Set(edges.map((e) => e.to));
  const r = nodes.filter((n) => !hasIn.has(n.id)).map((n) => n.id);
  return r.length ? r : nodes.slice(0, 1).map((n) => n.id);
}

/**
 * Phones: a classification tree shows its roots and their children; the branches under a child open when it is in
 * `expanded`. Returns the visible nodes and edges plus, per visible node, how many direct children are hidden.
 */
export function visibleSubgraph(
  nodes: DiagramNode[],
  edges: DiagramEdge[],
  expanded: ReadonlySet<string>,
): { nodes: DiagramNode[]; edges: DiagramEdge[]; hiddenChildren: Map<string, number> } {
  const kids = childrenOf(edges);
  const visible = new Set<string>();
  const open = (id: string) => visible.has(id) && (roots(nodes, edges).includes(id) || expanded.has(id));
  const todo = [...roots(nodes, edges)];
  todo.forEach((r) => visible.add(r));
  while (todo.length) {
    const id = todo.shift()!;
    if (!open(id)) continue;
    for (const k of kids.get(id) ?? []) {
      if (!visible.has(k)) {
        visible.add(k);
        todo.push(k);
      }
    }
  }
  const hiddenChildren = new Map<string, number>();
  for (const id of visible) {
    const hidden = (kids.get(id) ?? []).filter((k) => !visible.has(k)).length;
    if (hidden) hiddenChildren.set(id, hidden);
  }
  return {
    nodes: nodes.filter((n) => visible.has(n.id)),
    edges: edges.filter((e) => visible.has(e.from) && visible.has(e.to)),
    hiddenChildren,
  };
}

/** Nodes in reading order (breadth-first from the roots, then any left over), for the hidden screen-reader list. */
export function readingOrder(nodes: DiagramNode[], edges: DiagramEdge[]): DiagramNode[] {
  const kids = childrenOf(edges);
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const seen = new Set<string>();
  const out: DiagramNode[] = [];
  const todo = [...roots(nodes, edges)];
  while (todo.length) {
    const id = todo.shift()!;
    if (seen.has(id) || !byId.has(id)) continue;
    seen.add(id);
    out.push(byId.get(id)!);
    todo.push(...(kids.get(id) ?? []));
  }
  for (const n of nodes) if (!seen.has(n.id)) out.push(n);
  return out;
}

/** Chip text for a cite: passages "[n]"-style numbers, ontology facts "F1", the answer's own graph facts "G1". */
export function citeLabel(c: { kind: 'passage' | 'fact'; n: number }, source: 'ontology' | 'answer' | null): string {
  if (c.kind === 'passage') return String(c.n);
  return `${source === 'answer' ? 'G' : 'F'}${c.n}`;
}

/** File-name slug: "medevolv-flowchart-<slug>.png". */
export function slugify(s: string | null | undefined): string {
  const slug = (s ?? '')
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/[\s_]+/g, '-')
    .replace(/-+/g, '-')
    .slice(0, 48)
    .replace(/-$/, '');
  return slug || 'diagram';
}
