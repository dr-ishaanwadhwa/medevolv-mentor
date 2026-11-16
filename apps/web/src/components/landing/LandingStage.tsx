'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';
import { LinkButton } from '@/components/ui';
import type { LandingMode } from './copy';
import { DATA_TIMEOUT_MS, mapCaption, staticReason } from './gate';
import './landing.css';

/** Client shell around the SSR scenes (PRD 4.L). The scenes render on the server as plain text panels, so the hero is
 * the first paint with no JavaScript. After paint, and only if the device can take it, this lazily imports three.js and
 * the scene (L-5), loads the library map with a 6 s time fallback, and loads the chiasm only near scene 3 (L-6).
 * Any failure leaves the static page: same text plus SVG art (L-9). */

type Phase = 'pending' | 'loading' | 'live' | 'static';

interface Conn { saveData?: boolean; effectiveType?: string }

function hasWebGL(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch {
    return false;
  }
}

/** Anonymous daily counters (api/events.py). Fire-and-forget; at most once per page load per name (PRD 5.3). */
const sent = new Set<string>();
function track(name: 'landing_view' | 'landing_cta') {
  if (sent.has(name)) return;
  sent.add(name);
  try {
    void fetch('/api/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
      keepalive: true,
    }).catch(() => {});
  } catch { /* counters never break the page */ }
}

export function LandingStage({
  children,
  bookLabels,
  heroBooks,
  whyBooks,
  ctaLabel,
}: {
  children: ReactNode;
  mode: LandingMode;
  /** story.json book order, with the names students use (passed from the server so story.json stays out of client JS) */
  bookLabels: string[];
  heroBooks: number[];
  whyBooks: number[];
  ctaLabel: string;
}) {
  const root = useRef<HTMLDivElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const labels = useRef<(HTMLSpanElement | null)[]>([]);
  const [phase, setPhase] = useState<Phase>('pending');
  const [caption, setCaption] = useState('');
  const [sticky, setSticky] = useState(false);

  // the 3D layer
  useEffect(() => {
    const conn = (navigator as Navigator & { connection?: Conn }).connection;
    const why = staticReason({ webgl: hasWebGL(), saveData: conn?.saveData, effectiveType: conn?.effectiveType });
    if (why) {
      setPhase('static');
      return;
    }
    const ctl = new AbortController();
    let scene: import('./scene').LandingScene | null = null;
    let mo: MutationObserver | null = null;
    let near: IntersectionObserver | null = null;
    let dead = false;
    const toStatic = (e: unknown) => {
      if (dead) return;
      console.warn('[landing] staying static', e);
      ctl.abort();
      setPhase('static');
    };

    // wait for the first paint (and an idle moment) before touching three.js
    const idle = (cb: () => void) => {
      const w = window as Window & { requestIdleCallback?: (f: () => void, o?: { timeout: number }) => number };
      if (w.requestIdleCallback) w.requestIdleCallback(cb, { timeout: 1500 });
      else window.setTimeout(cb, 200);
    };
    const begin = () => {
      if (dead) return;
      setPhase('loading');
      const mobile = window.innerWidth < 768;
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const timer = window.setTimeout(() => toStatic(new Error('library.bin not decoded within 6 s')), DATA_TIMEOUT_MS);
      Promise.all([import('./scene'), import('../story/data').then((m) => m.loadStory(mobile, ctl.signal))])
        .then(([mod, data]) => {
          window.clearTimeout(timer);
          if (dead || ctl.signal.aborted || !canvas.current || !stage.current || !root.current) return;
          const sections = Array.from(root.current.querySelectorAll<HTMLElement>('section[data-scene]'));
          scene = new mod.LandingScene({
            canvas: canvas.current,
            stage: stage.current,
            sections,
            labels: labels.current,
            data,
            dark: document.documentElement.classList.contains('dark'),
            mobile,
            reduced,
            heroBooks,
            whyBooks,
            onFatal: toStatic,
          });
          scene.start();
          setCaption(mapCaption(data.count, data.story.n));
          setPhase('live');
          mo = new MutationObserver(() => scene?.setTheme(document.documentElement.classList.contains('dark')));
          mo.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
          // scene 3's mesh: only when it is within one viewport (L-6)
          const body = root.current.querySelector('#landing-body');
          if (body) {
            near = new IntersectionObserver(([e]) => {
              if (e.isIntersecting) { scene?.loadChiasm(); near?.disconnect(); }
            }, { rootMargin: '100% 0px' });
            near.observe(body);
          }
        })
        .catch((e) => { window.clearTimeout(timer); toStatic(e); });
    };
    const raf = requestAnimationFrame(() => idle(begin));
    return () => {
      dead = true;
      cancelAnimationFrame(raf);
      ctl.abort();
      mo?.disconnect();
      near?.disconnect();
      scene?.destroy();
    };
  }, [heroBooks, whyBooks]);

  // counters, the from_landing marker, and the mobile sticky CTA (hidden while a scene's own primary CTA is visible)
  useEffect(() => {
    track('landing_view');
    const el = root.current;
    if (!el) return;
    const onClick = (e: MouseEvent) => {
      const a = (e.target as HTMLElement | null)?.closest('[data-landing-cta]');
      if (!a) return;
      try { sessionStorage.setItem('from_landing', '1'); } catch { /* private mode */ }
      track('landing_cta');
    };
    el.addEventListener('click', onClick);
    // shown once the hero CTA has scrolled away, until the last scene (it has the final CTA and sits above the footer)
    const hero = el.querySelector('[data-landing-cta="hero"]');
    const last = el.querySelector('#landing-more');
    let heroGone = false;
    let lastReached = false;
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        const above = e.boundingClientRect.top < 0;
        if (e.target === hero) heroGone = !e.isIntersecting && above;
        if (e.target === last) lastReached = e.isIntersecting || above;
      }
      setSticky(heroGone && !lastReached);
    });
    if (hero) io.observe(hero);
    if (last) io.observe(last);
    return () => { el.removeEventListener('click', onClick); io.disconnect(); };
  }, []);

  return (
    <div ref={root} className="ld-root" data-landing={phase}>
      <noscript>
        <style>{'.only-static{display:block!important}'}</style>
      </noscript>
      <div ref={stage} className="ld-stage" aria-hidden="true">
        {phase === 'loading' && <div className="ld-progress" />}
        {phase !== 'static' && <canvas ref={canvas} />}
        {bookLabels.map((label, i) => (
          <span key={label} ref={(n) => { labels.current[i] = n; }} className="ld-label">
            {label}
          </span>
        ))}
      </div>
      {/* the honest map caption (L-12) is real text, outside the aria-hidden stage */}
      {phase === 'live' && caption && (
        <p className="ld-caption pointer-events-none fixed bottom-[calc(var(--tabbar-h)+env(safe-area-inset-bottom)+4.5rem)] right-3 z-[1] md:bottom-3">
          {caption}
        </p>
      )}
      <div className="ld-scenes">{children}</div>
      <div className="ld-sticky" data-show={sticky ? 'true' : 'false'} inert={!sticky || undefined} aria-hidden={!sticky || undefined}>
        <LinkButton href="/ask" variant="primary" className="w-full" data-landing-cta="sticky" tip="landing.sticky">
          {ctaLabel}
        </LinkButton>
      </div>
    </div>
  );
}
