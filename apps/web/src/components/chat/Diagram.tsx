'use client';

/**
 * Flowchart renderer (PRD 4.1, D-2). Loaded lazily with next/dynamic from DiagramSlot, so dagre is never in the
 * initial /ask bundle (D-8). Boxes are HTML laid over an SVG of the arrows: labels are text nodes (LLM output is never
 * markup), citation chips are real buttons, colours are theme tokens. Exports are a separate light-palette SVG.
 */
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { BookMarked, Download, Maximize2, Minus, MoreHorizontal, Plus, X } from 'lucide-react';
import { Button, CitationChip, Drawer, StatusPill, Tooltip } from '@/components/ui';
import { sendFeedback, type AnswerCitation, type DiagramCite, type DiagramResponse, type GraphCitation } from '@/lib/api';
import { BADGE, STUDY_AID_LINE } from '@/lib/copy/diagram';
import { exportSvg, sourcePointers } from '@/lib/diagram/export';
import { citeLabel, readingOrder, slugify, visibleSubgraph } from '@/lib/diagram/graph';
import { CHIP_ROW_H, LINE_H, edgePath, layoutDiagram, type Layout, type LaidNode } from '@/lib/diagram/layout';
import { ANSWER_TIPS as T } from '@/lib/tips/answer';
import { cn } from '@/lib/cn';
import { useUi } from '@/store/ui';

const MIN_SCALE = 0.55;
const NARROW_PX = 560;

const pointer = (p: { book: string; edition?: string | null; chapter?: string | null; pages?: string | null }) =>
  [p.book + (p.edition ? ` ${p.edition}e` : ''), p.chapter, p.pages ? `p ${p.pages}` : ''].filter(Boolean).join(', ');

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [w, setW] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    setW(el.clientWidth);
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => setW(el.clientWidth));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

export default function Diagram({
  diagram,
  citations,
  onOpenSource,
}: {
  diagram: DiagramResponse;
  citations: AnswerCitation[];
  /** Opens the answer's source drawer at passage [n]. Fact chips never call this (D-11). */
  onOpenSource: (n: number) => void;
}) {
  const toast = useUi((s) => s.toast);
  const [wrapRef, width] = useWidth<HTMLDivElement>();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [factOpen, setFactOpen] = useState<number | null>(null);
  const [full, setFull] = useState(false);
  const [menu, setMenu] = useState(false);
  const [reported, setReported] = useState(false);
  const narrow = width > 0 && width < NARROW_PX;
  const collapsible = diagram.kind === 'classification' && narrow;

  const view = useMemo(() => {
    if (!collapsible) return { nodes: diagram.nodes, edges: diagram.edges, hidden: new Map<string, number>() };
    const v = visibleSubgraph(diagram.nodes, diagram.edges, expanded);
    return { nodes: v.nodes, edges: v.edges, hidden: v.hiddenChildren };
  }, [collapsible, diagram, expanded]);
  const layout = useMemo(
    () => layoutDiagram({ kind: diagram.kind, nodes: view.nodes, edges: view.edges, groups: diagram.groups }),
    [diagram.kind, diagram.groups, view],
  );
  const fullLayout = useMemo(() => layoutDiagram(diagram), [diagram]);
  const order = useMemo(() => readingOrder(diagram.nodes, diagram.edges), [diagram]);
  const facts = diagram.fact_sources;
  const scale = width ? Math.max(MIN_SCALE, Math.min(1, width / layout.width)) : 1;

  const toggle = (id: string) =>
    setExpanded((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const file = (ext: string) => `medevolv-flowchart-${slugify(diagram.subject ?? diagram.title)}.${ext}`;
  const buildSvg = () =>
    exportSvg(fullLayout, {
      title: diagram.title,
      source: diagram.source,
      pointers: sourcePointers(fullLayout, diagram.source, citations, facts),
      date: new Date(),
    });

  const saveSvg = () => {
    setMenu(false);
    download(new Blob([buildSvg().svg], { type: 'image/svg+xml' }), file('svg'));
  };
  const savePng = async () => {
    try {
      const png = await svgToPng(buildSvg());
      const f = new File([png], file('png'), { type: 'image/png' });
      if (typeof navigator.canShare === 'function' && navigator.canShare({ files: [f] })) {
        try {
          await navigator.share({ files: [f], title: diagram.title ?? 'Flowchart' });
          return;
        } catch (e) {
          if ((e as Error).name === 'AbortError') return; // the student closed the share sheet
        }
      }
      download(png, file('png'));
    } catch {
      toast('Could not make the image');
    }
  };
  const report = async () => {
    setMenu(false);
    try {
      await sendFeedback({ kind: 'diagram_wrong', target_id: diagram.diagram_id ?? undefined });
      setReported(true);
      toast('Thanks, that was recorded');
    } catch {
      toast('Could not send the report');
    }
  };

  const summary = `Flowchart${diagram.title ? `: ${diagram.title}` : ''}. ${diagram.nodes.length} boxes. ${BADGE[diagram.source ?? 'answer']}.`;

  const canvas = (l: Layout, s: number, interactive: boolean) => (
    <Canvas
      layout={l}
      scale={s}
      source={diagram.source}
      citations={citations}
      facts={facts}
      hidden={interactive ? view.hidden : new Map()}
      expanded={expanded}
      onToggle={interactive && collapsible ? toggle : undefined}
      onPassage={onOpenSource}
      onFact={setFactOpen}
      label={summary}
    />
  );

  return (
    <div className="rounded-xl border border-border bg-surface p-3 sm:p-4">
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill tone={diagram.source === 'ontology' ? 'good' : 'info'}>{BADGE[diagram.source ?? 'answer']}</StatusPill>
        <div className="ml-auto flex items-center gap-1.5">
          <Button size="sm" variant="secondary" onClick={savePng} tip={T['answer.diagram.save']}>
            <Download className="h-4 w-4" aria-hidden /> Save image
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setFull(true)} tip={T['answer.diagram.fullscreen']} iconOnly aria-label="Full screen">
            <Maximize2 className="h-4 w-4" aria-hidden />
          </Button>
          <div className="relative">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setMenu((m) => !m)}
              tip={T['answer.diagram.more']}
              iconOnly
              aria-label="More"
              aria-haspopup="menu"
              aria-expanded={menu}
            >
              <MoreHorizontal className="h-4 w-4" aria-hidden />
            </Button>
            {menu && (
              <div role="menu" className="absolute right-0 z-20 mt-1 w-48 rounded-xl border border-border bg-surface p-1 shadow-lg">
                <MenuItem tip={T['answer.diagram.svg']} onClick={saveSvg}>
                  Save as SVG
                </MenuItem>
                <MenuItem tip={T['answer.diagram.report']} onClick={report} disabled={reported || !diagram.diagram_id}>
                  {reported ? 'Reported' : 'Report a problem'}
                </MenuItem>
              </div>
            )}
          </div>
        </div>
      </div>
      {diagram.title && <h4 className="mt-2 text-[0.95rem] font-semibold leading-snug">{diagram.title}</h4>}

      <div ref={wrapRef} className="mt-3 overflow-x-auto">
        {canvas(layout, scale, true)}
      </div>
      {collapsible && <p className="mt-1 text-xs text-muted">Tap + on a box to open its branches.</p>}

      <ol className="sr-only" aria-label="Flowchart boxes in reading order">
        {order.map((n) => (
          <li key={n.id}>
            {n.label}. Sources: {n.cites.map((c) => (c.kind === 'passage' ? `passage ${c.n}` : `fact ${citeLabel(c, diagram.source)}`)).join(', ')}.
          </li>
        ))}
      </ol>

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-border pt-2 text-xs text-muted">
        <span>{STUDY_AID_LINE}</span>
        {facts.length > 0 && (
          <Tooltip tip={T['answer.diagram.sources']}>
            <button type="button" onClick={() => setFactOpen(facts[0].n)} className="inline-flex min-h-[44px] items-center gap-1 text-accent hover:underline md:min-h-0">
              <BookMarked className="h-3.5 w-3.5" aria-hidden /> Diagram sources
            </button>
          </Tooltip>
        )}
      </div>

      <Drawer open={factOpen !== null} onClose={() => setFactOpen(null)} title="Diagram sources" eyebrow="Textbook facts">
        <FactList facts={facts} source={diagram.source} active={factOpen} />
      </Drawer>

      {full && (
        <FullScreen onClose={() => setFull(false)} title={diagram.title ?? 'Flowchart'}>
          {(zoom) => canvas(fullLayout, zoom, false)}
        </FullScreen>
      )}
    </div>
  );
}

function MenuItem({ tip, onClick, disabled, children }: { tip: (typeof T)[keyof typeof T]; onClick: () => void; disabled?: boolean; children: ReactNode }) {
  return (
    <Tooltip tip={tip}>
      <button
        type="button"
        role="menuitem"
        disabled={disabled}
        onClick={onClick}
        className="flex min-h-[44px] w-full items-center rounded-lg px-3 text-left text-sm hover:bg-surface2 disabled:opacity-50 md:min-h-[36px]"
      >
        {children}
      </button>
    </Tooltip>
  );
}

function Canvas({
  layout,
  scale,
  source,
  citations,
  facts,
  hidden,
  expanded,
  onToggle,
  onPassage,
  onFact,
  label,
}: {
  layout: Layout;
  scale: number;
  source: DiagramResponse['source'];
  citations: AnswerCitation[];
  facts: GraphCitation[];
  hidden: Map<string, number>;
  expanded: Set<string>;
  onToggle?: (id: string) => void;
  onPassage: (n: number) => void;
  onFact: (n: number) => void;
  label: string;
}) {
  return (
    <div style={{ width: layout.width * scale, height: layout.height * scale }} className="relative mx-auto">
      <div
        role="img"
        aria-label={label}
        style={{ width: layout.width, height: layout.height, transform: `scale(${scale})`, transformOrigin: '0 0' }}
        className="absolute left-0 top-0"
      >
        <svg width={layout.width} height={layout.height} className="absolute inset-0" aria-hidden>
          <defs>
            <marker id="mm-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" className="fill-muted" />
            </marker>
          </defs>
          {layout.groups.map((g) => (
            <g key={g.id}>
              <rect x={g.x} y={g.y} width={g.w} height={g.h} rx={12} className="fill-accent-soft stroke-border" fillOpacity={0.55} />
              <text x={g.x + 12} y={g.y + 15} className="fill-accent text-[11.5px] font-semibold">
                {g.title}
              </text>
            </g>
          ))}
          {layout.edges.map((e) => (
            <g key={`${e.from}-${e.to}`}>
              <path d={edgePath(e.points)} fill="none" className="stroke-muted" strokeWidth={1.3} markerEnd="url(#mm-arrow)" />
              {e.label && e.lx !== undefined && e.ly !== undefined && (
                <text x={e.lx} y={e.ly + 4} textAnchor="middle" className="fill-muted stroke-surface text-[11px]" strokeWidth={4} paintOrder="stroke">
                  {e.label}
                </text>
              )}
            </g>
          ))}
        </svg>
        {layout.nodes.map((n) => (
          <Box
            key={n.id}
            n={n}
            source={source}
            citations={citations}
            facts={facts}
            hiddenKids={hidden.get(n.id) ?? 0}
            open={expanded.has(n.id)}
            onToggle={onToggle}
            onPassage={onPassage}
            onFact={onFact}
          />
        ))}
      </div>
    </div>
  );
}

function Box({
  n,
  source,
  citations,
  facts,
  hiddenKids,
  open,
  onToggle,
  onPassage,
  onFact,
}: {
  n: LaidNode;
  source: DiagramResponse['source'];
  citations: AnswerCitation[];
  facts: GraphCitation[];
  hiddenKids: number;
  open: boolean;
  onToggle?: (id: string) => void;
  onPassage: (n: number) => void;
  onFact: (n: number) => void;
}) {
  const warn = n.role === 'warning';
  return (
    <div
      style={{ left: n.x, top: n.y, width: n.w, height: n.h }}
      className={cn(
        'absolute flex flex-col justify-between rounded-[10px] border px-3 py-[9px] text-[13px] text-ink',
        warn ? 'border-bad bg-bad-soft' : 'border-border bg-surface2',
        n.role === 'start' && 'border-2 font-semibold',
      )}
    >
      <div style={{ lineHeight: `${LINE_H}px` }}>
        {n.lines.map((l, i) => (
          <span key={i} className="block whitespace-nowrap">
            {l}
          </span>
        ))}
      </div>
      {n.cites.length > 0 && (
        <div className="flex items-center gap-1" style={{ height: CHIP_ROW_H }}>
          {n.cites.map((c) => (
            <Cite key={`${c.kind}${c.n}`} c={c} source={source} citations={citations} facts={facts} onPassage={onPassage} onFact={onFact} />
          ))}
          {onToggle && (hiddenKids > 0 || open) && (
            <Tooltip tip={T['answer.diagram.branch']} iconOnly>
              <button
                type="button"
                aria-expanded={open}
                aria-label={open ? `Hide the boxes under ${n.label}` : `Show ${hiddenKids} more under ${n.label}`}
                onClick={() => onToggle(n.id)}
                className="ml-auto inline-flex h-5 min-w-5 items-center justify-center rounded border border-border bg-surface px-1 text-[11px] text-muted"
              >
                {open ? <Minus className="h-3 w-3" aria-hidden /> : `+${hiddenKids}`}
              </button>
            </Tooltip>
          )}
        </div>
      )}
    </div>
  );
}

function Cite({
  c,
  source,
  citations,
  facts,
  onPassage,
  onFact,
}: {
  c: DiagramCite;
  source: DiagramResponse['source'];
  citations: AnswerCitation[];
  facts: GraphCitation[];
  onPassage: (n: number) => void;
  onFact: (n: number) => void;
}) {
  if (c.kind === 'passage') {
    const p = citations.find((x) => x.index === c.n);
    return (
      <CitationChip
        n={c.n}
        onClick={onPassage}
        tip={{ purpose: p ? `Source ${c.n}: ${pointer(p)}.` : `Source ${c.n} of the answer.`, effect: 'Opens the passage.' }}
      />
    );
  }
  const f = facts.find((x) => x.n === c.n);
  const label = citeLabel(c, source);
  return (
    <Tooltip tip={{ purpose: f ? `Textbook fact ${label}: ${pointer(f)}.` : `Textbook fact ${label}.`, effect: 'Opens the diagram sources list.' }} iconOnly>
      <button
        type="button"
        onClick={() => onFact(c.n)}
        aria-label={`Open fact ${label}`}
        className="inline-flex h-5 items-center rounded border border-accent/50 bg-surface px-1 font-mono text-[10.5px] font-semibold text-accent"
      >
        {label}
      </button>
    </Tooltip>
  );
}

function FactList({ facts, source, active }: { facts: GraphCitation[]; source: DiagramResponse['source']; active: number | null }) {
  const ref = useRef<HTMLOListElement>(null);
  useEffect(() => {
    if (active === null) return;
    ref.current?.querySelector(`[data-n="${active}"]`)?.scrollIntoView({ block: 'nearest' });
  }, [active]);
  return (
    <ol ref={ref} className="space-y-2">
      {facts.map((f) => (
        <li
          key={f.n}
          data-n={f.n}
          className={cn('rounded-lg border p-3 text-sm', f.n === active ? 'border-accent bg-accent-soft/50' : 'border-border')}
        >
          <div className="font-mono text-xs font-semibold text-accent">{citeLabel({ kind: 'fact', n: f.n }, source)}</div>
          <div className="mt-0.5 font-medium">{f.book}{f.edition ? `, ${f.edition}e` : ''}</div>
          {(f.chapter || f.pages) && (
            <div className="text-muted">
              {[f.chapter, f.pages ? `p ${f.pages}` : ''].filter(Boolean).join(' · ')}
            </div>
          )}
          <div className="mt-1 font-mono text-[0.68rem] text-muted">{f.fact_id}</div>
        </li>
      ))}
    </ol>
  );
}

function FullScreen({ onClose, title, children }: { onClose: () => void; title: string; children: (zoom: number) => ReactNode }) {
  const [zoom, setZoom] = useState(1);
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      prev?.focus?.();
    };
  }, [onClose]);
  return (
    <div role="dialog" aria-modal="true" aria-label={title} className="fixed inset-0 z-50 flex flex-col bg-bg">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <span className="truncate text-sm font-semibold">{title}</span>
        <div className="ml-auto flex items-center gap-1">
          <Button size="sm" variant="ghost" iconOnly aria-label="Zoom out" tip={T['answer.diagram.zoomOut']} onClick={() => setZoom((z) => Math.max(0.4, +(z - 0.2).toFixed(2)))}>
            <Minus className="h-4 w-4" aria-hidden />
          </Button>
          <Button size="sm" variant="ghost" iconOnly aria-label="Zoom in" tip={T['answer.diagram.zoomIn']} onClick={() => setZoom((z) => Math.min(2.5, +(z + 0.2).toFixed(2)))}>
            <Plus className="h-4 w-4" aria-hidden />
          </Button>
          <Button ref={closeRef} size="sm" variant="secondary" iconOnly aria-label="Close full screen" tip={T['answer.diagram.close']} onClick={onClose}>
            <X className="h-4 w-4" aria-hidden />
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4">{children(zoom)}</div>
      <p className="border-t border-border px-3 py-2 text-xs text-muted">{STUDY_AID_LINE}</p>
    </div>
  );
}

function download(blob: Blob, name: string) {
  const u = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = u;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(u), 1000);
}

/** Draws the export SVG at 2x onto a white canvas. */
function svgToPng({ svg, width, height }: { svg: string; width: number; height: number }): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const u = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }));
    img.onload = () => {
      const c = document.createElement('canvas');
      c.width = width * 2;
      c.height = height * 2;
      const ctx = c.getContext('2d');
      if (!ctx) return reject(new Error('no canvas'));
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, c.width, c.height);
      ctx.scale(2, 2);
      ctx.drawImage(img, 0, 0, width, height);
      URL.revokeObjectURL(u);
      c.toBlob((b) => (b ? resolve(b) : reject(new Error('no png'))), 'image/png');
    };
    img.onerror = () => {
      URL.revokeObjectURL(u);
      reject(new Error('svg failed to load'));
    };
    img.src = u;
  });
}
