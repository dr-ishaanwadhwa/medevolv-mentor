/**
 * Layered flowchart layout with @dagrejs/dagre (PRD D-2). Top-to-bottom for sequence, pathway, case and drug;
 * left-to-right for classification. Only the lazily loaded diagram chunk imports this file.
 */
import * as dagre from '@dagrejs/dagre';
import type { DiagramEdge, DiagramKind, DiagramNode } from '../api';
import { wrapLabel } from './graph';

export const FONT_PX = 13;
export const LINE_H = 17;
const CHAR_W = 7.1; // a generous average for Instrument Sans at 13 px, so text never overflows its box
const PAD_X = 12;
const PAD_Y = 9;
export const CHIP_ROW_H = 22;
const GROUP_PAD = 14;
export const GROUP_TITLE_H = 18;

export interface LaidNode extends DiagramNode {
  /** top-left corner */
  x: number;
  y: number;
  w: number;
  h: number;
  lines: string[];
}
export interface LaidEdge extends DiagramEdge {
  points: { x: number; y: number }[];
  /** label centre, when the edge has a label */
  lx?: number;
  ly?: number;
}
export interface LaidGroup {
  id: string;
  title: string;
  x: number;
  y: number;
  w: number;
  h: number;
}
export interface Layout {
  width: number;
  height: number;
  nodes: LaidNode[];
  edges: LaidEdge[];
  groups: LaidGroup[];
  rankdir: 'TB' | 'LR';
}

export function nodeSize(label: string, hasChips: boolean): { w: number; h: number; lines: string[] } {
  const lines = wrapLabel(label);
  const longest = Math.max(...lines.map((l) => l.length), 6);
  return {
    lines,
    w: Math.round(Math.max(96, longest * CHAR_W + PAD_X * 2)),
    h: Math.round(lines.length * LINE_H + PAD_Y * 2 + (hasChips ? CHIP_ROW_H : 0)),
  };
}

export function layoutDiagram(d: {
  kind: DiagramKind | null;
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  groups: { id: string; title: string }[];
}): Layout {
  const rankdir = d.kind === 'classification' ? 'LR' : 'TB';
  const ids = new Set(d.nodes.map((n) => n.id));
  const usedGroups = d.groups.filter((g) => d.nodes.some((n) => n.group === g.id));
  const g = new dagre.graphlib.Graph({ compound: usedGroups.length > 0, multigraph: false });
  g.setGraph({ rankdir, nodesep: 22, ranksep: usedGroups.length ? 46 : 38, edgesep: 12, marginx: 12, marginy: 12 + (usedGroups.length ? GROUP_TITLE_H : 0) });
  g.setDefaultEdgeLabel(() => ({}));
  const sizes = new Map<string, { w: number; h: number; lines: string[] }>();
  for (const n of d.nodes) {
    const s = nodeSize(n.label, n.cites.length > 0);
    sizes.set(n.id, s);
    g.setNode(n.id, { width: s.w, height: s.h });
  }
  for (const grp of usedGroups) g.setNode(`group:${grp.id}`, { paddingTop: GROUP_PAD + GROUP_TITLE_H, paddingBottom: GROUP_PAD, paddingLeft: GROUP_PAD, paddingRight: GROUP_PAD } as never);
  for (const n of d.nodes) if (n.group && usedGroups.some((x) => x.id === n.group)) g.setParent(n.id, `group:${n.group}`);
  const edges = d.edges.filter((e) => ids.has(e.from) && ids.has(e.to));
  for (const e of edges)
    g.setEdge(e.from, e.to, e.label ? { label: e.label, width: e.label.length * 6.4 + 8, height: 14, labelpos: 'c' } : {});
  dagre.layout(g);

  const nodes: LaidNode[] = d.nodes.map((n) => {
    const p = g.node(n.id) as unknown as { x: number; y: number; width: number; height: number };
    const s = sizes.get(n.id)!;
    return { ...n, x: p.x - s.w / 2, y: p.y - s.h / 2, w: s.w, h: s.h, lines: s.lines };
  });
  const laidEdges: LaidEdge[] = edges.map((e) => {
    const ge = g.edge(e.from, e.to) as unknown as { points: { x: number; y: number }[]; x?: number; y?: number };
    return { ...e, points: ge.points ?? [], lx: e.label ? ge.x : undefined, ly: e.label ? ge.y : undefined };
  });
  const groups: LaidGroup[] = usedGroups.map((grp) => {
    // The band encloses its member boxes (computed from them, not trusted from dagre's cluster box).
    const mem = nodes.filter((n) => n.group === grp.id);
    const x0 = Math.min(...mem.map((n) => n.x)) - GROUP_PAD;
    const y0 = Math.min(...mem.map((n) => n.y)) - GROUP_PAD - GROUP_TITLE_H;
    const x1 = Math.max(...mem.map((n) => n.x + n.w)) + GROUP_PAD;
    const y1 = Math.max(...mem.map((n) => n.y + n.h)) + GROUP_PAD;
    return { id: grp.id, title: grp.title, x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
  });

  const xs = [...nodes.map((n) => n.x), ...groups.map((b) => b.x), ...laidEdges.flatMap((e) => e.points.map((p) => p.x))];
  const ys = [...nodes.map((n) => n.y), ...groups.map((b) => b.y), ...laidEdges.flatMap((e) => e.points.map((p) => p.y))];
  const minX = Math.min(...xs) - 12;
  const minY = Math.min(...ys) - 12;
  const shift = <T extends { x: number; y: number }>(o: T): T => ({ ...o, x: o.x - minX, y: o.y - minY });
  const out = {
    nodes: nodes.map(shift),
    groups: groups.map(shift),
    edges: laidEdges.map((e) => ({
      ...e,
      points: e.points.map(shift),
      lx: e.lx === undefined ? undefined : e.lx - minX,
      ly: e.ly === undefined ? undefined : e.ly - minY,
    })),
  };
  const maxX = Math.max(...out.nodes.map((n) => n.x + n.w), ...out.groups.map((b) => b.x + b.w), ...out.edges.flatMap((e) => e.points.map((p) => p.x)));
  const maxY = Math.max(...out.nodes.map((n) => n.y + n.h), ...out.groups.map((b) => b.y + b.h), ...out.edges.flatMap((e) => e.points.map((p) => p.y)));
  return { ...out, width: Math.ceil(maxX + 12), height: Math.ceil(maxY + 12), rankdir };
}

/** SVG path through the edge points (straight segments; dagre already routes around boxes). */
export function edgePath(points: { x: number; y: number }[]): string {
  return points.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
}
