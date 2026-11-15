'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { ArrowRight, Search, X } from 'lucide-react';
import { SkeletonLines, Tooltip } from '@/components/ui';
import { cn } from '@/lib/cn';
import { conceptHref, searchConcepts, typeMeta, type ConceptHit } from './api';

// Verified against /api/concepts/search.
const SUGGESTED: { label: string; id: string; type: string; hint: string }[] = [
  { label: 'Pheochromocytoma', id: '302835009', type: 'PathologicalCondition', hint: 'Why alpha-blockade comes before beta-blockade' },
  { label: 'Middle meningeal artery', id: 'MED:OKF/anatomicalstructure/middle-meningeal-artery', type: 'AnatomicalStructure', hint: 'The vessel behind an extradural bleed' },
  { label: 'Brachial plexus', id: 'MED:OKF/anatomicalstructure/brachial-plexus', type: 'AnatomicalStructure', hint: 'Roots, trunks and the injuries that map to them' },
  { label: 'Malaria', id: '61462000', type: 'PathologicalCondition', hint: 'Presentation, diagnosis and chemoprophylaxis' },
  { label: 'Optic chiasm', id: 'MED:OKF/anatomicalstructure/optic-chiasm', type: 'AnatomicalStructure', hint: 'Where pituitary tumours cause bitemporal field loss' },
];

function TypeDot({ type }: { type: string }) {
  return <span className="inline-block h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: typeMeta(type).color }} aria-hidden />;
}

export function TypePill({ type, className }: { type: string; className?: string }) {
  const m = typeMeta(type);
  return (
    <span
      className={cn('inline-flex items-center gap-1.5 rounded-full border border-border bg-surface2 px-2.5 py-0.5 text-xs font-medium text-ink', className)}
    >
      <span className="h-2 w-2 rounded-full" style={{ background: m.color }} aria-hidden />
      {m.label}
    </span>
  );
}

export function ExploreView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const initial = params.get('q') ?? '';
  const [q, setQ] = useState(initial);
  const [debounced, setDebounced] = useState(initial.trim());
  const [hits, setHits] = useState<ConceptHit[] | null>(null);
  const [state, setState] = useState<'idle' | 'loading' | 'ready' | 'error'>(initial.trim() ? 'loading' : 'idle');
  const [type, setType] = useState<string>('all');
  const [cursor, setCursor] = useState(0);
  const listRef = useRef<HTMLUListElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 200);
    return () => clearTimeout(t);
  }, [q]);

  // Keep ?q= in the URL (replace, so Back leaves Explore rather than stepping through keystrokes).
  useEffect(() => {
    const next = debounced ? `${pathname}?q=${encodeURIComponent(debounced)}` : pathname;
    window.history.replaceState(window.history.state, '', next);
  }, [debounced, pathname]);

  useEffect(() => {
    if (debounced.length < 2) {
      setHits(null);
      setState('idle');
      return;
    }
    const ctl = new AbortController();
    setState('loading');
    searchConcepts(debounced, ctl.signal, 40)
      .then((r) => {
        setHits(r);
        setState('ready');
        setType('all');
        setCursor(0);
      })
      .catch((e) => {
        if (!ctl.signal.aborted) setState('error');
        void e;
      });
    return () => ctl.abort();
  }, [debounced]);

  const types = useMemo(() => {
    const counts = new Map<string, number>();
    hits?.forEach((h) => counts.set(h.type, (counts.get(h.type) ?? 0) + 1));
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [hits]);

  const shown = useMemo(() => (hits ?? []).filter((h) => type === 'all' || h.type === type), [hits, type]);

  useEffect(() => {
    listRef.current?.querySelector<HTMLElement>('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' });
  }, [cursor]);

  const open = useCallback((id: string) => router.push(conceptHref(id)), [router]);

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, shown.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (e.key === 'Enter' && shown[cursor]) {
      e.preventDefault();
      open(shown[cursor].id);
    } else if (e.key === 'Escape') {
      setQ('');
    }
  };

  const searching = debounced.length >= 2;

  return (
    <div className="page py-6 md:py-10">
      <h1 className="text-2xl font-semibold md:text-3xl">Explore</h1>
      <p className="mt-1.5 max-w-xl text-[0.95rem] text-muted">
        Search the concept graph built from the textbooks. Every concept page lists where the books discuss it and what it links to.
      </p>

      <div className="relative mt-5">
        <Search className="pointer-events-none absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-muted" aria-hidden />
        <input
          ref={inputRef}
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={onKey}
          role="combobox"
          aria-expanded={shown.length > 0}
          aria-controls="concept-results"
          aria-activedescendant={shown[cursor] ? `res-${cursor}` : undefined}
          aria-label="Search concepts"
          placeholder="Search a condition, structure, drug or sign…"
          className="h-[52px] w-full rounded-2xl border border-border bg-surface pl-11 pr-11 text-base text-ink shadow-card outline-none placeholder:text-muted focus:border-accent focus:ring-2 focus:ring-accent/20"
        />
        {q && (
          <Tooltip tip="explore.clear" iconOnly>
          <button
            type="button"
            aria-label="Clear search"
            onClick={() => {
              setQ('');
              inputRef.current?.focus();
            }}
            className="absolute right-2 top-1/2 grid h-10 w-10 -translate-y-1/2 place-items-center rounded-xl text-muted hover:bg-surface2"
          >
            <X className="h-4 w-4" />
          </button>
          </Tooltip>
        )}
      </div>

      {searching && types.length > 1 && (
        <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Filter by type">
          {[['all', hits?.length ?? 0] as const, ...types].map(([t, n]) => (
            <Tooltip key={t} tip="explore.filter">
            <button
              type="button"
              aria-pressed={type === t}
              onClick={() => {
                setType(t);
                setCursor(0);
              }}
              className={cn(
                'inline-flex min-h-[40px] items-center gap-1.5 rounded-full border px-3.5 text-sm transition-colors md:min-h-[34px]',
                type === t ? 'border-accent bg-accent-soft font-medium text-ink' : 'border-border bg-surface text-muted hover:text-ink',
              )}
            >
              {t !== 'all' && <TypeDot type={t} />}
              {t === 'all' ? 'All' : typeMeta(t).label}
              <span className="font-mono text-[0.72rem] text-muted">{n}</span>
            </button>
            </Tooltip>
          ))}
        </div>
      )}

      <div className="mt-4" aria-live="polite">
        {state === 'loading' && !hits && (
          <div className="card p-4">
            <SkeletonLines lines={5} />
          </div>
        )}
        {state === 'error' && (
          <p className="rounded-xl bg-warn-soft px-4 py-3 text-sm text-warn">Search is unavailable right now. Check the connection and try again.</p>
        )}
        {searching && state !== 'error' && hits && shown.length === 0 && (
          <div className="card p-6 text-center">
            <p className="font-medium">No concepts match &ldquo;{debounced}&rdquo;</p>
            <p className="mt-1 text-sm text-muted">Try a shorter or more general term, or one of the suggestions below.</p>
          </div>
        )}
        {shown.length > 0 && (
          <ul
            id="concept-results"
            ref={listRef}
            role="listbox"
            className={cn('card divide-y divide-border overflow-hidden transition-opacity', state === 'loading' && 'opacity-60')}
          >
            {shown.map((h, i) => (
              <li key={h.id} id={`res-${i}`} role="option" aria-selected={i === cursor} data-tip-id="explore.result">
                <Tooltip tip="explore.result">
                <Link
                  href={conceptHref(h.id)}
                  onMouseEnter={() => setCursor(i)}
                  className={cn('flex min-h-[56px] items-center justify-between gap-3 px-4 py-2.5', i === cursor ? 'bg-accent-soft' : 'hover:bg-surface2')}
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{h.label}</span>
                    <span className="mt-0.5 flex items-center gap-2 text-xs text-muted">
                      <TypeDot type={h.type} />
                      {typeMeta(h.type).label}
                      <span aria-hidden>·</span>
                      {h.degree} {h.degree === 1 ? 'link' : 'links'}
                    </span>
                  </span>
                  <ArrowRight className="h-4 w-4 shrink-0 text-muted" aria-hidden />
                </Link>
                </Tooltip>
              </li>
            ))}
          </ul>
        )}
      </div>

      {(!searching || (hits && shown.length === 0)) && (
        <section className="mt-8" aria-labelledby="suggested">
          <h2 id="suggested" className="label-mono mb-3">
            Try one of these
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {SUGGESTED.map((s) => (
              <Tooltip key={s.id} tip="explore.suggested">
              <Link href={conceptHref(s.id)} className="card group flex min-h-[88px] flex-col justify-between gap-2 p-4 transition-colors hover:border-accent/50 hover:bg-accent-soft/60">
                <div className="flex items-start justify-between gap-2">
                  <span className="font-semibold leading-snug">{s.label}</span>
                  <TypePill type={s.type} />
                </div>
                <span className="text-sm text-muted">{s.hint}</span>
              </Link>
              </Tooltip>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
