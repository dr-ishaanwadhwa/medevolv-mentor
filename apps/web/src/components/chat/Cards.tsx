'use client';

import { RotateCcw, ServerCrash } from 'lucide-react';
import { Button, Chip } from '@/components/ui';
import { DEMO_PROMPTS } from '@/lib/demo';

export function ErrorCard({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-card border border-bad/30 bg-bad-soft/60 p-4">
      <div className="flex items-start gap-3">
        <ServerCrash className="mt-0.5 h-5 w-5 shrink-0 text-bad" aria-hidden />
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-bad">That did not go through</h3>
          <p className="mt-1 text-sm leading-relaxed">{message || 'The server could not answer right now.'}</p>
          <p className="mt-1 text-xs text-muted">Nothing was answered, so there is nothing to trust or cite here.</p>
          {onRetry && (
            <Button size="sm" variant="secondary" className="mt-3" onClick={onRetry}>
              <RotateCcw className="h-4 w-4" /> Try again
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

/** Shown for declined / refused answers: what happened and what to do next. */
export function NextSteps({
  kind,
  onEdit,
  onPick,
}: {
  kind: 'personal_refusal' | 'decline';
  onEdit?: () => void;
  onPick?: (q: string) => void;
}) {
  return (
    <div className="rounded-xl bg-surface2/60 p-3.5">
      <div className="label-mono mb-2">What you can do next</div>
      <ul className="mb-3 space-y-1 text-sm text-muted">
        {kind === 'personal_refusal' ? (
          <li>Ask about the concept instead, for example how a drug class works, rather than what you should take.</li>
        ) : (
          <>
            <li>Rephrase with the clinical term or the structure you mean.</li>
            <li>Ask about one topic at a time, or try a demo question below.</li>
          </>
        )}
      </ul>
      <div className="flex flex-wrap gap-2">
        {onEdit && (
          <Chip onClick={onEdit}>
            Edit and re-ask
          </Chip>
        )}
        {onPick &&
          DEMO_PROMPTS.slice(0, 3).map((d) => (
            <Chip key={d.text} onClick={() => onPick(d.text)} className="max-w-full">
              <span className="truncate">{d.tag}</span>
            </Chip>
          ))}
      </div>
    </div>
  );
}
