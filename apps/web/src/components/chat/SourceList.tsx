'use client';

import { BookOpen } from 'lucide-react';
import type { AnswerCitation } from '@/lib/api';
import { citationWhere } from '@/lib/format';
import { Tooltip } from '@/components/ui';

/** Compact "where this comes from" list: book · chapter · pages. Opens the drawer on click. */
export function SourceList({ citations, onOpen }: { citations: AnswerCitation[]; onOpen: (n: number) => void }) {
  const cited = citations.filter((c) => c.cited);
  const rest = citations.length - cited.length;
  if (!citations.length) return null;
  if (!cited.length) {
    // Declined answers: no evidence was cited, so don't dress retrieval up as sources.
    return (
      <Tooltip tip="answer.sources.closest">
      <button
        type="button"
        onClick={() => onOpen(citations[0].index)}
        className="min-h-[44px] text-sm text-accent underline-offset-4 hover:underline md:min-h-0"
      >
        See the closest passages the search found ({citations.length}), none were cited
      </button>
      </Tooltip>
    );
  }
  return (
    <div>
      <div className="label-mono mb-2 flex items-center gap-1.5">
        <BookOpen className="h-3.5 w-3.5" aria-hidden /> Sources
      </div>
      {cited.length > 0 ? (
        <ul className="divide-y divide-border rounded-xl border border-border">
          {cited.map((c) => {
            const w = citationWhere(c);
            return (
              <li key={c.index}>
                <Tooltip tip="answer.sources.item">
                <button
                  type="button"
                  onClick={() => onOpen(c.index)}
                  className="flex min-h-[44px] w-full items-start gap-3 px-3 py-2.5 text-left hover:bg-surface2"
                >
                  <span aria-hidden className="cite-chip mt-0.5 shrink-0">{c.index}</span>
                  <span className="min-w-0 text-[0.88rem] leading-snug">
                    <span className="font-medium">{w.book}</span>
                    <span className="block font-mono text-[0.74rem] text-muted">
                      {[w.chapter, w.pages].filter(Boolean).join(' · ')}
                    </span>
                  </span>
                </button>
                </Tooltip>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="text-sm text-muted">No passage was cited.</p>
      )}
      {rest > 0 && (
        <Tooltip tip="answer.sources.uncited">
        <button
          type="button"
          onClick={() => onOpen((citations.find((c) => !c.cited) ?? citations[0]).index)}
          className="mt-2 min-h-[44px] text-sm text-accent underline-offset-4 hover:underline md:min-h-0"
        >
          {rest} more retrieved, not cited
        </button>
        </Tooltip>
      )}
    </div>
  );
}
