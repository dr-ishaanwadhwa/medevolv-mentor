'use client';

import { useEffect, useRef } from 'react';
import { Drawer, StatusPill } from '@/components/ui';
import type { AnswerCitation } from '@/lib/api';
import { citationWhere, clip } from '@/lib/format';
import { cn } from '@/lib/cn';

function Source({ c, active }: { c: AnswerCitation; active: boolean }) {
  const ref = useRef<HTMLLIElement>(null);
  useEffect(() => {
    if (active) ref.current?.scrollIntoView({ block: 'nearest' });
  }, [active]);
  const w = citationWhere(c);
  return (
    <li
      ref={ref}
      id={`src-${c.index}`}
      className={cn(
        'rounded-xl border bg-surface p-3.5',
        c.cited ? 'border-l-4 border-border border-l-accent' : 'border-border',
        active && 'ring-2 ring-accent/60',
      )}
    >
      <div className="flex items-start gap-2.5">
        <span className={cn('mt-0.5 font-mono text-sm font-semibold', c.cited ? 'text-accent' : 'text-muted')}>[{c.index}]</span>
        <div className="min-w-0 flex-1">
          <div className="text-[0.92rem] font-medium leading-snug">{w.book}</div>
          <div className="mt-1 flex flex-wrap gap-x-2 gap-y-0.5 font-mono text-[0.76rem] text-muted">
            {w.chapter && <span>{w.chapter}</span>}
            {w.pages && <span>{w.pages}</span>}
          </div>
          {c.excerpt && <p className="mt-2 text-[0.86rem] leading-relaxed text-muted">“{clip(c.excerpt, 300)}”</p>}
        </div>
      </div>
    </li>
  );
}

/** Shared by Ask and Why. `active` is the [n] that was clicked. */
export function SourceDrawer({
  citations,
  active,
  onClose,
}: {
  citations: AnswerCitation[];
  active: number | null;
  onClose: () => void;
}) {
  const cited = citations.filter((c) => c.cited);
  const retrieved = citations.filter((c) => !c.cited);
  const missing = active != null && !citations.some((c) => c.index === active);
  return (
    <Drawer open={active != null} onClose={onClose} eyebrow="Textbook sources" title={`Source${active != null ? ` [${active}]` : 's'}`}>
      {missing && <p className="mb-3 text-sm text-warn">Source [{active}] is not in the list the server returned.</p>}
      {cited.length > 0 && (
        <section className="mb-5">
          <div className="mb-2 flex items-center gap-2">
            <StatusPill tone="good">Cited in the answer</StatusPill>
          </div>
          <ul className="space-y-2.5">
            {cited.map((c) => (
              <Source key={c.index} c={c} active={c.index === active} />
            ))}
          </ul>
        </section>
      )}
      {retrieved.length > 0 && (
        <section>
          <div className="mb-1 flex items-center gap-2">
            <StatusPill tone="neutral">Retrieved, not cited</StatusPill>
          </div>
          <p className="mb-2 text-xs text-muted">Found by the search but not used as evidence in the answer text.</p>
          <ul className="space-y-2.5">
            {retrieved.map((c) => (
              <Source key={c.index} c={c} active={c.index === active} />
            ))}
          </ul>
        </section>
      )}
      <p className="mt-5 text-xs leading-relaxed text-muted">
        Pointers to the book, chapter and page. Check the printed edition before relying on a detail.
      </p>
    </Drawer>
  );
}
