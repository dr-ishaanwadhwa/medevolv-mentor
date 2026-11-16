'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Box } from 'lucide-react';
import AtlasCanvas from '@/components/canvas/AtlasCanvas';
import { LinkButton } from '@/components/ui';
import { useAtlasStore } from '@/lib/atlas-store';
import { ModelCredit } from '@/components/credits/ModelCredit';
import type { ConceptPage } from './api';

/** FMA ids from an atlas deep link (`...?select=FMA1,FMA2`). */
function idsFromLink(link: string | null): string[] {
  if (!link) return [];
  try {
    const sel = new URL(link, 'http://x').searchParams.get('select') ?? '';
    return sel.split(',').map((s) => s.trim()).filter((s) => /^FMA\d+$/i.test(s));
  } catch {
    return [];
  }
}

/** Compact 3D panel. Renders nothing unless the concept maps onto the 3D atlas (navigation only, never a clinical claim). */
export function Concept3D({ concept }: { concept: ConceptPage }) {
  // Always the male model here (F-7): the female model is only ever requested by the full atlas viewer.
  const atlas = useAtlasStore((s) => s.atlases.male);
  const loadManifest = useAtlasStore((s) => s.loadManifest);
  const linkIds = useMemo(() => idsFromLink(concept.atlas.link), [concept.atlas.link]);

  const names = useMemo(() => {
    const out = concept.atlas.structures.flatMap((s) => [s.atlas_name, s.label]);
    if (concept.type === 'AnatomicalStructure') out.push(concept.label, ...concept.aliases);
    return [...new Set(out.map((n) => n.toLowerCase().trim()).filter(Boolean))];
  }, [concept]);

  const wantsLookup = linkIds.length === 0 && names.length > 0;
  useEffect(() => {
    if (wantsLookup) void loadManifest('male');
  }, [wantsLookup, loadManifest]);

  const ids = useMemo(() => {
    if (linkIds.length) return linkIds;
    if (!atlas || !names.length) return [];
    const wanted = new Set(names);
    const hit = atlas.concepts.find((c) => c.elements.length > 0 && wanted.has(c.name.toLowerCase()));
    return hit ? [hit.id] : [];
  }, [linkIds, atlas, names]);

  // Only start fetching geometry once the panel scrolls near the viewport.
  const box = useRef<HTMLDivElement>(null);
  const [near, setNear] = useState(false);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (e) => {
        if (e.some((x) => x.isIntersecting)) {
          setNear(true);
          io.disconnect();
        }
      },
      { rootMargin: '200px' },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [ids.length]);

  if (!ids.length) return null;
  const href = `/atlas?select=${ids.join(',')}`;

  return (
    <section className="card overflow-hidden" aria-labelledby="c3d">
      <div className="flex items-center justify-between gap-3 px-4 pb-2 pt-3.5">
        <div>
          <h2 id="c3d" className="label-mono">
            In 3D
          </h2>
          <p className="mt-0.5 text-xs text-muted">Navigation only: shows where it sits, not a clinical claim.</p>
        </div>
        <LinkButton href={href} size="sm" variant="primary" tip="explore.in3d" className="shrink-0">
          <Box className="h-4 w-4" aria-hidden /> Open in 3D Atlas
        </LinkButton>
      </div>
      <div ref={box} className="relative h-[280px] bg-[radial-gradient(ellipse_at_50%_40%,rgb(var(--c-surface2))_0%,rgb(var(--c-surface))_75%)] md:h-[320px]">
        {near && <AtlasCanvas compact highlight={ids} autoRotate sex="male" />}
      </div>
      <ModelCredit model="bodyparts3d" className="px-4 pb-3 pt-2" />
    </section>
  );
}
