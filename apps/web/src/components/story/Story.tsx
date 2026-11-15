'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { LinkButton } from '@/components/ui';
import { renderMarkdown } from '@/components/ui/Markdown';
import HowClassic from '@/app/how/HowClassic';
import { CHAPTERS, RAIL_LABELS } from './narration';
import { bookNick, loadStory, type StoryData } from './data';
import { bookColor } from './palette';
import type { StoryController } from './controller';
import './story.css';

const HEIGHTS = [200, 460, 320, 220, 240, 240, 230, 300, 200, 200]; // dvh per chapter
const EVALS: [string, string, number, number][] = [
  ['39/39', 'questions got the right behaviour: answer, decline or refuse', 39, 39],
  ['30/30', 'answers carried at least one citation', 30, 30],
  ['90.8%', 'correct chapter in the top 3 search results (Tripathi, 446 questions)', 90.8, 0],
];

function hasWebGL(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch { return false; }
}

function CountUp({ to, active, reduced, fmt, dur = 1400 }: { to: number; active: boolean; reduced: boolean; fmt: (v: number) => string; dur?: number }) {
  const [v, setV] = useState(reduced ? to : 0);
  const started = useRef(false);
  useEffect(() => {
    if (!active || started.current) return;
    started.current = true;
    if (reduced) { setV(to); return; }
    const t0 = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - t0) / dur);
      setV(to * (1 - Math.pow(1 - t, 3)));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active, to, dur, reduced]);
  return <>{fmt(v)}</>;
}

export default function Story() {
  const [failed, setFailed] = useState(false);
  const [data, setData] = useState<StoryData | null>(null);
  const mobile = useMemo(() => typeof window !== 'undefined' && window.innerWidth < 768, []);

  useEffect(() => {
    if (!hasWebGL()) { setFailed(true); return; }
    const ac = new AbortController();
    loadStory(mobile, ac.signal).then(setData).catch((e) => { if (!ac.signal.aborted) { console.warn('[how] data failed', e); setFailed(true); } });
    return () => ac.abort();
  }, [mobile]);

  if (failed) return <HowClassic />;
  if (!data) return <div className="st-loading">Loading the library map…</div>;
  return <Scene data={data} mobile={mobile} onFail={() => setFailed(true)} />;
}

function Scene({ data, mobile, onFail }: { data: StoryData; mobile: boolean; onFail: () => void }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const ctl = useRef<StoryController | null>(null);
  const [active, setActive] = useState(0);
  const reduced = useMemo(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches, []);
  const { story } = data;
  const books = story.books;
  const evidence = story.journey?.evidence ?? [];
  const answerHtml = useMemo(() => renderMarkdown(story.answer ?? ''), [story.answer]);
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));
  const [libCount, setLibCount] = useState(false);

  useEffect(() => {
    const mo = new MutationObserver(() => setDark(document.documentElement.classList.contains('dark')));
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => mo.disconnect();
  }, []);

  useEffect(() => {
    let c: StoryController | null = null;
    let dead = false;
    (async () => {
      try {
        const { StoryController } = await import('./controller');
        if (dead) return;
        c = new StoryController({
          canvas: canvasRef.current!, root: rootRef.current!, stage: stageRef.current!, data,
          dark: document.documentElement.classList.contains('dark'), mobile, reduced,
          onActive: setActive, onFatal: (e) => { console.warn('[how] render failed', e); onFail(); },
        });
        ctl.current = c;
        c.start();
        setLibCount(true);
      } catch (e) { console.warn('[how] init failed', e); onFail(); }
    })();
    return () => { dead = true; c?.destroy(); ctl.current = null; };
  }, [data, mobile, reduced, onFail]);

  useEffect(() => { ctl.current?.setTheme(dark); }, [dark]);
  const jump = useCallback((k: number) => ctl.current?.jump(k), []);
  const fmtInt = (v: number) => Math.round(v).toLocaleString('en-US');
  const subs = data.subs;

  const whereOf = (e: (typeof evidence)[number]) => {
    const t = books.find((b) => b.id === e.book)?.title ?? '';
    return t && e.where.startsWith(t + ', ') ? e.where.slice(t.length + 2) : e.where;
  };
  const decl = story.declined;

  return (
    <div ref={rootRef} className="st-root" data-story>
      <div ref={stageRef} className="st-stage">
        <canvas ref={canvasRef} aria-hidden="true" />
        <div className="st-scrim" aria-hidden="true" />

        {/* decorative overlays that track 3D points */}
        <div className="st-ui" aria-hidden="true">
          {books.map((b, i) => (
            <div key={b.id} className="st-abs" data-booklabel={i}><span className="st-booklabel">{bookNick[b.id] ?? b.title}<span>{b.count.toLocaleString('en-US')}</span></span></div>
          ))}
          <div className="st-abs" data-chip="query"><div className="st-chipi"><b>Question</b><span className="st-q">{story.journey.question}</span></div></div>
          {story.refusal && (
            <>
              <div className="st-abs" data-chip="refuse"><div className="st-chipi st-left st-chip-bad"><b>Question</b><span className="st-q">{story.refusal.question}</span></div></div>
              <div className="st-abs" data-tag="refuse"><span className="st-tag st-left" style={{ marginLeft: 0, transform: 'translateX(-100%)' }}>Refused before search</span></div>
            </>
          )}
          {subs.map((q, k) => (
            <div key={k} className="st-abs" data-chip={`sub-${k}`}>
              <div className={`st-chipi ${k % 2 === 0 ? 'st-left' : ''}`}>
                <b>Sub-question {k + 1}</b>
                <span className="st-subtext st-q" data-text>{q}</span>
              </div>
            </div>
          ))}
          {subs.map((_, k) => (
            <div key={k} className="st-abs" data-chip={`best-${k}`}><span className="st-sim">best {(story.journey.near[Math.min(k, story.journey.near.length - 1)]?.neighbours.reduce((a, b) => Math.max(a, b.sim), 0) ?? 0).toFixed(3)}</span></div>
          ))}
          {decl && (
            <div className="st-abs" data-chip="declined">
              <div className="st-chipi st-left" style={{ maxWidth: '12.5rem' }}>
                <b>Not in the books</b>
                <span className="st-q">{decl.question}</span>
                <div className="st-gauge"><i style={{ width: `${decl.best * 100}%` }} /><u style={{ left: `${story.min_similarity * 100}%` }} /></div>
                <div className="st-gauge-l"><span>best {decl.best.toFixed(3)}</span><span>cut-off {story.min_similarity.toFixed(2)}</span></div>
              </div>
            </div>
          )}
        </div>

        {/* readable layer: cards + answer (real text) */}
        <div className="st-ui">
          <svg className="st-lines" data-lines aria-hidden="true" />
          <div className="st-cards" data-cards-wrap role="list" aria-label="Evidence passages sent to the model">
            {evidence.map((e, j) => {
              const bi = Math.max(0, books.findIndex((b) => b.id === e.book));
              return (
                <div key={e.n} role="listitem" className="st-card st-abs-card" data-card={j} data-cited={e.cited ? '1' : '0'} style={{ opacity: 0, visibility: 'hidden' }}>
                  <span className="st-n" data-card-dot={j}>{e.n}</span>
                  <span className="st-bk"><i style={{ background: bookColor(e.book, bi, dark) }} /><span>{bookNick[e.book] ?? e.book}</span></span>
                  <span className="st-wh">{whereOf(e)}</span>
                  <span className="st-st st-st-c">Cited in the answer</span>
                  <span className="st-st st-st-u">Retrieved, not cited</span>
                </div>
              );
            })}
          </div>
          <div className="st-answer" data-answer style={{ opacity: 0, visibility: 'hidden' }}>
            <div className="st-answer-h">The answer, as shown</div>
            {/* eslint-disable-next-line react/no-danger -- marked output, raw HTML escaped */}
            <div className="md" dangerouslySetInnerHTML={{ __html: answerHtml }} />
          </div>
          <div className="st-abs" data-atlas-still><div className="st-still">Optic chiasm · 3D model loading…</div></div>
          <div className="st-abs" data-atlas-tag><div className="st-atag"><span>Optic chiasm · FMA62045</span><span className="st-nav-tag">Navigation only</span></div></div>
          <div className="st-cue" data-cue>Scroll<i /></div>

          <a className="st-skip" href="/how?classic=1" aria-label="Skip the story"><span className="md:hidden">Skip</span><span className="hidden md:inline">Skip the story</span></a>
          <nav className="st-rail" aria-label="Story chapters">
            {CHAPTERS.map((c, k) => (
              <button key={c.id} type="button" className="st-dot" aria-label={`Chapter ${k + 1}: ${RAIL_LABELS[c.id]}`} aria-current={active === k ? 'step' : undefined} onClick={() => jump(k)}>
                <i /><span>{RAIL_LABELS[c.id]}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      {CHAPTERS.map((c, k) => (
        <section key={c.id} data-section={k} className="st-sec" style={{ height: `${HEIGHTS[k]}dvh` }} aria-labelledby={`st-h-${c.id}`}>
          <div className="st-sticky h-page">
            <div className="st-panel" data-panel={k} style={k === 0 ? undefined : { opacity: 0 }}>
              <div className="st-kicker">{String(k + 1).padStart(2, '0')} · {c.kicker}</div>
              {k === 0 ? (
                <>
                  <div className="mt-4 hidden md:block">
                    <div className="st-count" aria-hidden="true"><CountUp to={story.n} active={libCount} reduced={reduced} fmt={fmtInt} dur={1800} /></div>
                    <div className="st-count-l">textbook passages</div>
                  </div>
                  <h1 id={`st-h-${c.id}`} className="st-title st-title-hero">{c.title}</h1>
                </>
              ) : (
                <h2 id={`st-h-${c.id}`} className="st-title">{c.title}</h2>
              )}
              <p className="st-body">{c.body}</p>
              {c.id === 'books' && (
                <ul className="st-legend" aria-label="The seven books">
                  {books.map((b, i) => (
                    <li key={b.id} data-legend={i}><span className="st-sw" style={{ background: bookColor(b.id, i, dark) }} />{bookNick[b.id] ?? b.title}<em>{b.count.toLocaleString('en-US')}</em></li>
                  ))}
                </ul>
              )}
              {c.id === 'measured' && (
                <>
                  <div className="st-stats">
                    {EVALS.map(([big, what, a, b], i) => (
                      <div key={big} className="st-stat">
                        <strong aria-label={big}>
                          <CountUp to={a} active={active === 9} reduced={reduced} dur={1300 + i * 250}
                            fmt={(v) => (i === 2 ? `${v.toFixed(1)}%` : `${Math.round(v)}/${b}`)} />
                        </strong>
                        <span>{what}</span>
                      </div>
                    ))}
                  </div>
                  <p className="st-caveat">Results on our own question sets, not a clinical-safety guarantee. Retrieval is not yet measured for every book. A study aid, not medical advice.</p>
                  <div className="st-cta">
                    <LinkButton href="/" variant="primary" size="lg">Ask a question</LinkButton>
                    <LinkButton href="/why" size="lg">Why was I wrong?</LinkButton>
                  </div>
                </>
              )}
              <p className="st-cap"><span className="st-live" aria-hidden="true" /><span>{c.onscreen}</span></p>
            </div>
          </div>
        </section>
      ))}
    </div>
  );
}
