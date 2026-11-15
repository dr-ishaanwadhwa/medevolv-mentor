'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ChevronDown, Compass, Network } from 'lucide-react';
import { Chip, LinkButton, Skeleton, SkeletonLines, Tag } from '@/components/ui';
import { cn } from '@/lib/cn';
import { Concept3D } from './Concept3D';
import { TypePill } from './ExploreView';
import { GraphLegend, LocalGraph } from './LocalGraph';
import { bookName, conceptHref, fetchConcept, NotFoundError, typeMeta, cachedConcept, type ConceptPage, type LinkRef } from './api';

const humanize = (p: string) => {
  const s = p.toLowerCase().replace(/_/g, ' ');
  return s.charAt(0).toUpperCase() + s.slice(1);
};

function Section({ id, title, children, aside }: { id: string; title: string; children: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <section aria-labelledby={id} className="mt-8 first:mt-0">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 id={id} className="text-lg font-semibold">
          {title}
        </h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

function LinkGroups({ links, tierTag }: { links: LinkRef[]; tierTag?: string }) {
  const [openAll, setOpenAll] = useState<Record<string, boolean>>({});
  const groups = useMemo(() => {
    const m = new Map<string, LinkRef[]>();
    links.forEach((l) => {
      const k = l.predicate ?? 'related';
      m.set(k, [...(m.get(k) ?? []), l]);
    });
    return [...m.entries()].sort((a, b) => b[1].length - a[1].length);
  }, [links]);
  const LIMIT = 10;
  return (
    <div className="space-y-4">
      {groups.map(([pred, items]) => {
        const expanded = openAll[pred];
        const list = expanded ? items : items.slice(0, LIMIT);
        return (
          <div key={pred}>
            <div className="mb-1.5 flex items-center gap-2">
              <span className="text-sm font-medium text-muted">{humanize(pred)}</span>
              {tierTag && <Tag>{tierTag}</Tag>}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {list.map((l) => (
                <Chip key={l.id} href={conceptHref(l.id)} className="text-[0.84rem]">
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: typeMeta(l.type).color }} aria-hidden />
                  {l.label}
                </Chip>
              ))}
              {items.length > LIMIT && (
                <button
                  type="button"
                  onClick={() => setOpenAll((o) => ({ ...o, [pred]: !expanded }))}
                  className="min-h-[36px] rounded-full px-3 text-sm text-accent hover:bg-accent-soft"
                >
                  {expanded ? 'Show fewer' : `+${items.length - LIMIT} more`}
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function ConceptView({ id }: { id: string }) {
  const router = useRouter();
  const [page, setPage] = useState<ConceptPage | null>(() => cachedConcept(id) ?? null);
  const [state, setState] = useState<'loading' | 'ready' | 'notfound' | 'error'>(() => (cachedConcept(id) ? 'ready' : 'loading'));
  const [seeAlso, setSeeAlso] = useState(false);
  const [allSections, setAllSections] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const hit = cachedConcept(id);
    if (hit) {
      setPage(hit);
      setState('ready');
      return;
    }
    const ctl = new AbortController();
    setState('loading');
    setPage(null);
    fetchConcept(id, ctl.signal)
      .then((p) => {
        setPage(p);
        setState('ready');
      })
      .catch((e) => {
        if (ctl.signal.aborted) return;
        setState(e instanceof NotFoundError ? 'notfound' : 'error');
      });
    return () => ctl.abort();
  }, [id, attempt]);

  useEffect(() => {
    setSeeAlso(false);
    setAllSections(false);
    window.scrollTo({ top: 0 });
  }, [id]);

  useEffect(() => {
    if (page) document.title = `${page.label} · MedEvolv Mentor`;
  }, [page]);

  const back = () => {
    if (window.history.length > 1) router.back();
    else router.push('/explore');
  };

  const graphTypes = useMemo(() => [...new Set(page?.graph.nodes.map((n) => n.type) ?? [])], [page]);

  const backBtn = (
    <button
      type="button"
      onClick={back}
      className="-ml-2 mb-3 inline-flex min-h-[44px] items-center gap-1.5 rounded-xl px-2 text-sm text-muted hover:bg-surface2 hover:text-ink"
    >
      <ArrowLeft className="h-4 w-4" aria-hidden /> Back
    </button>
  );

  if (state === 'notfound' || state === 'error') {
    return (
      <div className="page py-6 md:py-10">
        {backBtn}
        <div className="card mx-auto max-w-md p-8 text-center">
          <Compass className="mx-auto h-8 w-8 text-muted" aria-hidden />
          <h1 className="mt-3 text-xl font-semibold">{state === 'notfound' ? 'Concept not found' : 'Could not load this concept'}</h1>
          <p className="mt-1.5 text-sm text-muted">
            {state === 'notfound'
              ? 'This concept is not in the textbook graph. It may have been renamed.'
              : 'The service did not respond. Check the connection and try again.'}
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            {state === 'error' && (
              <button type="button" onClick={() => setAttempt((a) => a + 1)} className="min-h-[44px] rounded-xl border border-border px-4 text-sm font-medium hover:bg-surface2">
                Try again
              </button>
            )}
            <LinkButton href="/explore" variant="primary">
              Search concepts
            </LinkButton>
          </div>
        </div>
      </div>
    );
  }

  if (!page) {
    return (
      <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 md:py-10" role="status" aria-label="Loading concept">
        <Skeleton className="mb-5 h-9 w-24" />
        <Skeleton className="h-9 w-2/3" />
        <Skeleton className="mt-3 h-6 w-40" />
        <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_440px]">
          <div className="space-y-6">
            <SkeletonLines lines={6} />
            <SkeletonLines lines={4} />
          </div>
          <Skeleton className="h-[380px] rounded-card" />
        </div>
      </div>
    );
  }

  const sections = allSections ? page.sections : page.sections.slice(0, 6);
  const hasGraph = page.graph.nodes.length > 1;

  return (
    <article className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 md:py-10">
      {backBtn}
      <header className="animate-fade-up">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <TypePill type={page.type} />
          {page.books.map((b) => (
            <Tag key={b}>{bookName(b)}</Tag>
          ))}
        </div>
        <h1 className="text-[1.75rem] font-semibold leading-tight md:text-4xl">{page.label}</h1>
        {page.aliases.length > 0 && (
          <p className="mt-2 text-[0.95rem] text-muted">
            Also called <span className="text-ink">{page.aliases.join(' · ')}</span>
          </p>
        )}
      </header>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_440px] lg:items-start">
        {/* Visuals: first on mobile, sticky right column on desktop */}
        <div className="space-y-4 lg:sticky lg:top-6 lg:order-2">
          {hasGraph && (
            <section className="card overflow-hidden" aria-labelledby="cgraph">
              <div className="px-4 pb-1 pt-3.5">
                <h2 id="cgraph" className="label-mono flex items-center gap-1.5">
                  <Network className="h-3.5 w-3.5" aria-hidden /> Local graph
                </h2>
                <div className="mt-2">
                  <GraphLegend types={graphTypes} />
                </div>
              </div>
              <div className="h-[340px] md:h-[400px]">
                <LocalGraph key={page.id} graph={page.graph} />
              </div>
            </section>
          )}
          <Concept3D key={page.id} concept={page} />
        </div>

        <div className="min-w-0 lg:order-1">
          <Section id="books" title="Where the books discuss it" aside={<span className="text-xs text-muted">{page.sections.length} sections</span>}>
            {page.sections.length === 0 ? (
              <p className="text-sm text-muted">No textbook sections are indexed for this concept.</p>
            ) : (
              <>
                <ul className="card divide-y divide-border overflow-hidden">
                  {sections.map((s) => (
                    <li key={s.section_id} className="px-4 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium leading-snug">{s.title}</span>
                        {s.primary && <Tag className="bg-accent-soft text-accent">primary</Tag>}
                      </div>
                      <div className="mt-1 text-[0.82rem] leading-snug text-muted">
                        <span className="font-medium text-ink/80">{bookName(s.book_id)}</span>
                        {s.path ? <> · {s.path.split(' › ').slice(0, -1).join(' › ') || s.path}</> : null}
                      </div>
                    </li>
                  ))}
                </ul>
                {page.sections.length > 6 && (
                  <button type="button" onClick={() => setAllSections((v) => !v)} className="mt-2 min-h-[40px] rounded-lg px-1 text-sm text-accent hover:underline">
                    {allSections ? 'Show fewer sections' : `Show all ${page.sections.length} sections`}
                  </button>
                )}
              </>
            )}
          </Section>

          {page.links_out.length > 0 && (
            <Section id="links-out" title="Links to" aside={<span className="text-xs text-muted">{page.links_out_total ?? page.links_out.length} certified</span>}>
              <LinkGroups links={page.links_out} />
            </Section>
          )}

          {page.links_in.length > 0 && (
            <Section id="links-in" title="Linked from" aside={<span className="text-xs text-muted">{page.links_in_total ?? page.links_in.length}</span>}>
              <LinkGroups links={page.links_in} tierTag="derived" />
            </Section>
          )}

          {page.hubs.length > 0 && (
            <Section id="hubs" title="Part of">
              <div className="flex flex-wrap gap-1.5">
                {page.hubs.map((h) => (
                  <Chip key={h.hub_id} href={`/explore?q=${encodeURIComponent(h.label)}`}>
                    {h.label}
                  </Chip>
                ))}
              </div>
            </Section>
          )}

          {page.see_also.length > 0 && (
            <Section id="see-also" title="See also" aside={<Tag>suggested</Tag>}>
              <button
                type="button"
                aria-expanded={seeAlso}
                onClick={() => setSeeAlso((v) => !v)}
                className="flex min-h-[44px] w-full items-center justify-between rounded-xl border border-border bg-surface px-4 text-left text-sm hover:bg-surface2"
              >
                <span>
                  {page.see_also.length} concepts often discussed alongside this one
                  <span className="text-muted"> · co-mentioned in the books, not a verified relation</span>
                </span>
                <ChevronDown className={cn('h-4 w-4 shrink-0 text-muted transition-transform', seeAlso && 'rotate-180')} aria-hidden />
              </button>
              {seeAlso && (
                <ul className="mt-2 flex flex-wrap gap-1.5">
                  {page.see_also.map((s) => (
                    <li key={s.id ?? s.label}>
                      {s.id ? <Chip href={conceptHref(s.id)}>{s.label}</Chip> : <Tag className="min-h-[34px] px-3 text-sm normal-case tracking-normal">{s.label}</Tag>}
                    </li>
                  ))}
                </ul>
              )}
            </Section>
          )}

          <p className="mt-10 text-xs text-muted">
            <Link href="/explore" className="underline underline-offset-2 hover:text-ink">
              Search another concept
            </Link>
          </p>
        </div>
      </div>
    </article>
  );
}
