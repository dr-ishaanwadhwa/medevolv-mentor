/**
 * "Save image" (PRD 4.1, D-7): a standalone SVG of the flowchart, always on white with the LIGHT palette whatever the
 * current theme, with the title, the study-aid line and the source pointers in the footer. The PNG is this SVG drawn
 * at 2x onto a canvas (in the component). Labels are escaped text nodes, never markup.
 */
import type { AnswerCitation, GraphCitation } from '../api';
import { STUDY_AID_LINE } from '../copy/diagram';
import { citeLabel, wrapLabel } from './graph';
import { CHIP_ROW_H, FONT_PX, LINE_H, type Layout } from './layout';

/** Light-theme tokens from globals.css (:root), fixed so exports look the same in dark mode. */
export const LIGHT = {
  bg: '#ffffff',
  surface2: 'rgb(238,243,244)',
  ink: 'rgb(21,35,42)',
  muted: 'rgb(90,107,114)',
  border: 'rgb(215,224,226)',
  accent: 'rgb(15,107,116)',
  accentSoft: 'rgb(226,240,241)',
  bad: 'rgb(176,50,58)',
  badSoft: 'rgb(248,227,228)',
  warnSoft: 'rgb(251,240,219)',
} as const;

export function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

const ptr = (book: string, edition?: string | null, chapter?: string | null, pages?: string | null) =>
  [book + (edition ? ` ${edition}e` : ''), chapter || '', pages ? `p ${pages}` : ''].filter(Boolean).join(', ');

/** "[1] Book 8e, Chapter, p 140" pointers for every cite the diagram uses (passages, then facts). No quote text. */
export function sourcePointers(
  layout: Pick<Layout, 'nodes' | 'edges'>,
  source: 'ontology' | 'answer' | null,
  citations: Pick<AnswerCitation, 'index' | 'book' | 'edition' | 'chapter' | 'pages'>[],
  facts: GraphCitation[],
): string[] {
  const used = new Map<string, { kind: 'passage' | 'fact'; n: number }>();
  for (const c of [...layout.nodes.flatMap((n) => n.cites), ...layout.edges.flatMap((e) => e.cites)])
    used.set(`${c.kind}${c.n}`, c);
  const sorted = [...used.values()].sort((a, b) => (a.kind === b.kind ? a.n - b.n : a.kind === 'passage' ? -1 : 1));
  const out: string[] = [];
  for (const c of sorted) {
    const p = c.kind === 'passage' ? citations.find((x) => x.index === c.n) : facts.find((x) => x.n === c.n);
    if (p) out.push(`[${citeLabel(c, source)}] ${ptr(p.book, p.edition, p.chapter, p.pages)}`);
  }
  return out;
}

export function footerText(pointers: string[], date: Date): string[] {
  const day = date.toISOString().slice(0, 10);
  return [`MedEvolv Mentor · ${STUDY_AID_LINE}`, ...(pointers.length ? [`Sources: ${pointers.join(' · ')}`] : []), day];
}

export function exportSvg(
  layout: Layout,
  meta: { title: string | null; source: 'ontology' | 'answer' | null; pointers: string[]; date: Date },
): { svg: string; width: number; height: number } {
  const pad = 24;
  const titleLines = meta.title ? wrapLabel(meta.title, 60) : [];
  const footer = footerText(meta.pointers, meta.date).flatMap((l) => wrapLabel(l, 96));
  const width = Math.max(layout.width + pad * 2, 520);
  const top = pad + titleLines.length * 22 + (titleLines.length ? 10 : 0);
  const ox = (width - layout.width) / 2;
  const height = top + layout.height + 16 + footer.length * 15 + pad;
  const t = (x: number, y: number, s: string, attrs = '') =>
    `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" ${attrs}>${esc(s)}</text>`;

  const parts: string[] = [];
  parts.push(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" font-family="Instrument Sans, Helvetica, Arial, sans-serif">`,
    `<rect width="100%" height="100%" fill="${LIGHT.bg}"/>`,
    `<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${LIGHT.muted}"/></marker></defs>`,
  );
  titleLines.forEach((l, i) => parts.push(t(pad, pad + 16 + i * 22, l, `font-size="17" font-weight="600" fill="${LIGHT.ink}"`)));
  parts.push(`<g transform="translate(${ox.toFixed(1)},${top})">`);
  for (const g of layout.groups) {
    parts.push(
      `<rect x="${g.x}" y="${g.y}" width="${g.w}" height="${g.h}" rx="12" fill="${LIGHT.accentSoft}" fill-opacity="0.55" stroke="${LIGHT.border}"/>`,
      t(g.x + 12, g.y + 15, g.title, `font-size="11.5" font-weight="600" fill="${LIGHT.accent}"`),
    );
  }
  for (const e of layout.edges) {
    const d = e.points.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    parts.push(`<path d="${d}" fill="none" stroke="${LIGHT.muted}" stroke-width="1.3" marker-end="url(#arr)"/>`);
    if (e.label && e.lx !== undefined && e.ly !== undefined)
      parts.push(t(e.lx, e.ly + 4, e.label, `font-size="11" fill="${LIGHT.muted}" text-anchor="middle" paint-order="stroke" stroke="${LIGHT.bg}" stroke-width="4"`));
  }
  for (const n of layout.nodes) {
    const warn = n.role === 'warning';
    parts.push(
      `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="10" fill="${warn ? LIGHT.badSoft : LIGHT.surface2}" stroke="${warn ? LIGHT.bad : LIGHT.border}" stroke-width="${n.role === 'start' ? 2 : 1}"/>`,
    );
    n.lines.forEach((l, i) =>
      parts.push(t(n.x + 12, n.y + 9 + FONT_PX + i * LINE_H, l, `font-size="${FONT_PX}" fill="${LIGHT.ink}"${n.role === 'start' ? ' font-weight="600"' : ''}`)),
    );
    if (n.cites.length)
      parts.push(
        t(n.x + 12, n.y + n.h - CHIP_ROW_H / 2 + 2, n.cites.map((c) => `[${citeLabel(c, meta.source)}]`).join(' '), `font-size="10.5" font-family="IBM Plex Mono, monospace" fill="${LIGHT.accent}"`),
      );
  }
  parts.push('</g>');
  footer.forEach((l, i) => parts.push(t(pad, top + layout.height + 22 + i * 15, l, `font-size="10.5" fill="${LIGHT.muted}"`)));
  parts.push('</svg>');
  return { svg: parts.join(''), width, height };
}
