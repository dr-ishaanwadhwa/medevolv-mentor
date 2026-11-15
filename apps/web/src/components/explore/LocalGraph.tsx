'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type Simulation, type SimulationLinkDatum, type SimulationNodeDatum } from 'd3-force';
import { conceptHref, typeMeta, type ConceptPage } from './api';

interface GNode extends SimulationNodeDatum {
  id: string;
  label: string;
  type: string;
  center: boolean;
}
interface GLink extends SimulationLinkDatum<GNode> {
  predicate: string;
  tier: string;
}

const humanize = (p: string) => p.toLowerCase().replace(/_/g, ' ');
const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

/** 1-hop neighbourhood of a concept: d3-force on SVG. Drag nodes, hover for names, click to open. */
export function LocalGraph({ graph }: { graph: ConceptPage['graph'] }) {
  const router = useRouter();
  const wrap = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 640, h: 380 });
  const [, setTick] = useState(0);
  const [hover, setHover] = useState<string | null>(null);
  const [armed, setArmed] = useState<string | null>(null);
  const sim = useRef<Simulation<GNode, GLink> | null>(null);

  const { nodes, links } = useMemo(() => {
    const ids = new Set(graph.nodes.map((n) => n.id));
    const nodes: GNode[] = graph.nodes.map((n) => ({ id: n.id, label: n.label, type: n.type, center: !!n.center }));
    const links: GLink[] = graph.edges
      .filter((e) => ids.has(e.source) && ids.has(e.target) && e.source !== e.target)
      .map((e) => ({ source: e.source, target: e.target, predicate: e.predicate, tier: e.tier }));
    return { nodes, links };
  }, [graph]);

  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: Math.max(240, el.clientWidth), h: Math.max(260, el.clientHeight) }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const R = (n: GNode) => (n.center ? 15 : 8.5);

  useEffect(() => {
    const { w, h } = size;
    const many = nodes.length > 14;
    const s = forceSimulation<GNode>(nodes)
      .force('link', forceLink<GNode, GLink>(links).id((d) => d.id).distance(many ? Math.min(w, h) * 0.34 : 110).strength(0.5))
      .force('charge', forceManyBody<GNode>().strength(many ? -420 : -400))
      .force('x', forceX<GNode>(w / 2).strength(0.03))
      .force('y', forceY<GNode>(h / 2).strength(0.04))
      .force('collide', forceCollide<GNode>().radius((d) => R(d) + 9));
    const center = nodes.find((n) => n.center);
    if (center) {
      center.fx = w / 2;
      center.fy = h / 2;
    }
    const clamp = () => {
      for (const n of nodes) {
        const r = R(n) + 10;
        n.x = Math.max(r, Math.min(w - r, n.x ?? w / 2));
        n.y = Math.max(r, Math.min(h - r, n.y ?? h / 2));
      }
    };
    sim.current = s;
    if (reducedMotion()) {
      s.stop();
      s.tick(300);
      clamp();
      setTick((t) => t + 1);
    } else {
      let raf = 0;
      s.on('tick', () => {
        clamp();
        if (!raf)
          raf = requestAnimationFrame(() => {
            raf = 0;
            setTick((t) => t + 1);
          });
      });
      // Stop burning CPU once settled.
      s.on('end', () => {
        s.stop();
        setTick((t) => t + 1);
      });
    }
    return () => {
      s.stop();
      sim.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, links, size.w, size.h]);

  // ---- drag ----
  const drag = useRef<{ id: string; moved: boolean; sx: number; sy: number } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const toLocal = (e: React.PointerEvent) => {
    const r = svgRef.current!.getBoundingClientRect();
    return { x: ((e.clientX - r.left) / r.width) * size.w, y: ((e.clientY - r.top) / r.height) * size.h };
  };
  const onDown = (e: React.PointerEvent, n: GNode) => {
    (e.currentTarget as Element).setPointerCapture(e.pointerId);
    drag.current = { id: n.id, moved: false, sx: e.clientX, sy: e.clientY };
    const p = toLocal(e);
    n.fx = p.x;
    n.fy = p.y;
    if (!reducedMotion()) sim.current?.alphaTarget(0.25).restart();
  };
  const onMove = (e: React.PointerEvent, n: GNode) => {
    const d = drag.current;
    if (!d || d.id !== n.id) return;
    if (Math.hypot(e.clientX - d.sx, e.clientY - d.sy) > 4) d.moved = true;
    const p = toLocal(e);
    n.fx = p.x;
    n.fy = p.y;
    if (reducedMotion()) {
      n.x = p.x;
      n.y = p.y;
      setTick((t) => t + 1);
    }
  };
  const onUp = (e: React.PointerEvent, n: GNode) => {
    const d = drag.current;
    drag.current = null;
    if (!n.center) {
      n.fx = null;
      n.fy = null;
    }
    sim.current?.alphaTarget(0);
    if (!d || d.moved) return;
    if (n.center) return;
    if (e.pointerType === 'touch' && armed !== n.id) {
      setArmed(n.id);
      setHover(n.id);
      return;
    }
    router.push(conceptHref(n.id));
  };

  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  const active = hover ?? armed;
  const activeNode = active ? byId.get(active) : undefined;
  const showAll = nodes.length <= 8;

  if (nodes.length < 2) {
    return (
      <div ref={wrap} className="grid h-full min-h-[260px] place-items-center p-6 text-center text-sm text-muted">
        No linked concepts to draw for this one yet.
      </div>
    );
  }

  const nodePos = (n: GNode) => ({ x: n.x ?? size.w / 2, y: n.y ?? size.h / 2 });
  const endpoint = (l: GLink) => [l.source as GNode, l.target as GNode] as const;

  return (
    <div ref={wrap} className="relative h-full min-h-[300px] w-full touch-pan-y select-none">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${size.w} ${size.h}`}
        className="absolute inset-0 h-full w-full"
        role="group"
        aria-label={`Concept graph around ${nodes.find((n) => n.center)?.label ?? 'this concept'}`}
        onPointerLeave={() => setHover(null)}
      >
        <defs>
          {['certified', 'derived', 'suggested'].map((t) => (
            <marker key={t} id={`arrow-${t}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5.5" markerHeight="5.5" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" fill="rgb(var(--c-muted))" opacity={t === 'certified' ? 0.9 : 0.55} />
            </marker>
          ))}
        </defs>
        <g>
          {links.map((l, i) => {
            const [a, b] = endpoint(l);
            if (!a || typeof a !== 'object' || !b || typeof b !== 'object') return null;
            const pa = nodePos(a);
            const pb = nodePos(b);
            const dx = pb.x - pa.x;
            const dy = pb.y - pa.y;
            const len = Math.hypot(dx, dy) || 1;
            const x2 = pb.x - (dx / len) * (R(b) + 2);
            const y2 = pb.y - (dy / len) * (R(b) + 2);
            const on = active && (a.id === active || b.id === active);
            return (
              <line
                key={i}
                x1={pa.x}
                y1={pa.y}
                x2={x2}
                y2={y2}
                stroke="rgb(var(--c-muted))"
                strokeWidth={on ? 2 : l.tier === 'certified' ? 1.4 : 1.1}
                strokeDasharray={l.tier === 'certified' ? undefined : l.tier === 'derived' ? '5 4' : '2 4'}
                opacity={on ? 0.95 : l.tier === 'certified' ? 0.55 : 0.4}
                markerEnd={`url(#arrow-${l.tier === 'certified' || l.tier === 'derived' ? l.tier : 'suggested'})`}
              >
                <title>{`${endpoint(l)[0].label} ${humanize(l.predicate)} ${endpoint(l)[1].label} (${l.tier})`}</title>
              </line>
            );
          })}
        </g>
        <g>
          {nodes.map((n) => {
            const p = nodePos(n);
            const color = typeMeta(n.type).color;
            const labelled = n.center || showAll || active === n.id;
            return (
              <g
                key={n.id}
                transform={`translate(${p.x},${p.y})`}
                role="link"
                tabIndex={n.center ? -1 : 0}
                aria-label={n.center ? `${n.label} (this concept)` : `Open ${n.label}`}
                className={n.center ? 'cursor-default' : 'cursor-pointer'}
                style={{ touchAction: 'none' }}
                onPointerDown={(e) => onDown(e, n)}
                onPointerMove={(e) => onMove(e, n)}
                onPointerUp={(e) => onUp(e, n)}
                onPointerCancel={() => (drag.current = null)}
                onPointerEnter={(e) => e.pointerType !== 'touch' && setHover(n.id)}
                onPointerLeave={(e) => e.pointerType !== 'touch' && setHover((h) => (h === n.id ? null : h))}
                onFocus={() => setHover(n.id)}
                onBlur={() => setHover(null)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !n.center) router.push(conceptHref(n.id));
                }}
              >
                {/* generous invisible hit target for touch */}
                <circle r={R(n) + 9} fill="transparent" />
                {n.center && <circle r={R(n) + 6} fill={color} opacity={0.18} />}
                <circle
                  r={R(n)}
                  fill={color}
                  stroke="rgb(var(--c-surface))"
                  strokeWidth={n.center ? 3 : 2}
                  opacity={active && active !== n.id && !n.center ? 0.75 : 1}
                />
                {labelled && (
                  <text
                    y={R(n) + 14}
                    textAnchor="middle"
                    fontSize={n.center ? 13 : 11.5}
                    fontWeight={n.center ? 650 : 500}
                    fill="rgb(var(--c-ink))"
                    stroke="rgb(var(--c-surface))"
                    strokeWidth={4}
                    paintOrder="stroke"
                    pointerEvents="none"
                  >
                    {n.label.length > 30 ? n.label.slice(0, 29) + '…' : n.label}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex min-h-[28px] items-end justify-between gap-2 px-3 pb-2 text-xs text-muted">
        <span className="truncate">
          {activeNode ? (
            <>
              <b className="font-semibold text-ink">{activeNode.label}</b> · {typeMeta(activeNode.type).label}
              {armed === activeNode.id && !activeNode.center ? ' · tap again to open' : ''}
            </>
          ) : (
            'Drag to rearrange · click a node to open it'
          )}
        </span>
      </div>
    </div>
  );
}

export function GraphLegend({ types }: { types: string[] }) {
  return (
    <ul className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted" aria-label="Legend">
      {types.map((t) => (
        <li key={t} className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: typeMeta(t).color }} aria-hidden />
          {typeMeta(t).label}
        </li>
      ))}
      <li className="inline-flex items-center gap-1.5">
        <svg width="22" height="6" aria-hidden>
          <line x1="0" y1="3" x2="22" y2="3" stroke="rgb(var(--c-muted))" strokeWidth="1.5" />
        </svg>
        certified
      </li>
      <li className="inline-flex items-center gap-1.5">
        <svg width="22" height="6" aria-hidden>
          <line x1="0" y1="3" x2="22" y2="3" stroke="rgb(var(--c-muted))" strokeWidth="1.5" strokeDasharray="5 4" />
        </svg>
        derived
      </li>
    </ul>
  );
}
