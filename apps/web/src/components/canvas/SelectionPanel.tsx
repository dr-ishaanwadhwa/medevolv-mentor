'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowUpRight, BookOpen, Info } from 'lucide-react';
import { Chip, SkeletonLines, Tag } from '@/components/ui';
import { useAtlasStore } from '@/lib/atlas-store';
import { conceptName } from '@/lib/anatomy';
import type { Sex } from '@/lib/atlas-sex';
import { Tooltip } from '@/components/ui/Tooltip';
import { ATLAS_TIPS, relatedTip } from '@/lib/tips/atlas';
import {
  bookName,
  conceptHref,
  fetchConcept,
  fetchSpatial,
  NotFoundError,
  typeMeta,
  type SpatialCitation,
  type SpatialResolve,
} from '@/components/explore/api';

interface Data {
  label: string;
  concept: SpatialResolve['concept'];
  citations: SpatialCitation[];
  related: SpatialResolve['related'];
}

/** Textbook pointers and related concepts for one atlas structure (GET /api/spatial/resolve). */
export function SelectionPanel({ fmaId, sex = 'male' }: { fmaId: string; sex?: Sex }) {
  const atlas = useAtlasStore((s) => s.atlases[sex]);
  const index = useAtlasStore((s) => s.indexes[sex]);
  const [data, setData] = useState<Data | null>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');

  useEffect(() => {
    if (!fmaId) return;
    const ctl = new AbortController();
    setState('loading');
    setData(null);
    (async () => {
      try {
        const r = await fetchSpatial(fmaId, ctl.signal, sex);
        setData({ label: r.label, concept: r.concept, citations: r.citations, related: r.related });
        setState('ready');
      } catch (e) {
        if (ctl.signal.aborted) return;
        // Fallback: look the structure up by name and show its book sections as pointers.
        const name = conceptName(atlas, index, fmaId);
        try {
          const c = await fetchConcept(name, ctl.signal);
          setData({
            label: c.label,
            concept: { id: c.id, label: c.label, type: c.type, aliases: c.aliases, degree: c.degree, books: c.books },
            citations: c.sections.slice(0, 8).map((s) => ({
              book: bookName(s.book_id),
              chapter: s.path.split(' › ').slice(0, 2).join(' › '),
              section_id: s.section_id,
            })),
            related: c.see_also
              .filter((x) => x.id)
              .slice(0, 8)
              .map((x) => ({ id: x.id as string, label: x.label, type: '', shared_facts: 0, tier: 'suggested' })),
          });
          setState('ready');
        } catch {
          if (!ctl.signal.aborted) setState(e instanceof NotFoundError ? 'ready' : 'error');
        }
      }
    })();
    return () => ctl.abort();
  }, [fmaId, atlas, index, sex]);

  const note = (
    <p className="mb-4 flex items-start gap-2 rounded-lg border border-border bg-surface2 px-3 py-2 text-[0.82rem] leading-snug text-muted">
      <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <span>
        <b className="font-semibold text-ink">Navigation only.</b> This highlight is not a clinical claim; it just shows where the
        structure sits and where the books discuss it.
      </span>
    </p>
  );

  if (state === 'loading') {
    return (
      <div>
        {note}
        <SkeletonLines lines={5} />
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div>
        {note}
        <p className="rounded-lg bg-warn-soft px-3 py-2 text-sm text-warn">Textbook details could not be loaded. Check the connection and select the structure again.</p>
      </div>
    );
  }

  const concept = data?.concept;
  const citations = data?.citations ?? [];
  const related = data?.related ?? [];

  return (
    <div>
      {note}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {concept && (
          <>
            <Tag>{typeMeta(concept.type).label}</Tag>
            {concept.aliases.slice(0, 3).map((a) => (
              <span key={a} className="text-xs text-muted">
                {a}
              </span>
            ))}
          </>
        )}
        <Tag>{fmaId}</Tag>
      </div>

      {concept && (
        <Tooltip tip={ATLAS_TIPS['atlas.panel.concept']}>
        <Link
          href={conceptHref(concept.id)}
          className="mb-5 inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-accent px-4 text-[0.92rem] font-medium text-accent-ink hover:bg-accent/90"
        >
          Open concept page <ArrowUpRight className="h-4 w-4" aria-hidden />
        </Link>
        </Tooltip>
      )}

      <h3 className="label-mono mb-2 flex items-center gap-1.5">
        <BookOpen className="h-3.5 w-3.5" aria-hidden /> Where the books discuss it
      </h3>
      {citations.length === 0 ? (
        <p className="mb-5 text-sm text-muted">
          {concept ? 'No textbook passages are linked to this structure yet.' : 'This structure is in the 3D model, but the textbook index has no concept page for it yet.'}
        </p>
      ) : (
        <ul className="mb-5 space-y-2.5">
          {citations.map((c, i) => (
            <li key={`${c.section_id}-${i}`} className="rounded-xl border border-border bg-bg/50 px-3 py-2.5">
              <div className="text-[0.86rem] font-medium leading-snug">
                {c.book}
                {c.chapter ? <span className="text-muted"> · {c.chapter}</span> : null}
                {c.pages ? <span className="text-muted"> · pp. {c.pages}</span> : null}
              </div>
              {c.excerpt && <p className="mt-1 text-[0.82rem] leading-relaxed text-muted">{c.excerpt}</p>}
            </li>
          ))}
        </ul>
      )}

      {related.length > 0 && (
        <>
          <h3 className="label-mono mb-2">Related concepts</h3>
          <div className="flex flex-wrap gap-1.5">
            {related.map((r) => (
              <Chip key={r.id} href={conceptHref(r.id)} tip={relatedTip(r.label)} className="text-[0.82rem]">
                {r.label}
              </Chip>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
