'use client';

import { useState } from 'react';
import { AlertTriangle, Check, ChevronDown, OctagonX } from 'lucide-react';
import type { StepEvent } from '@/lib/api';
import { fmtMs } from '@/lib/format';
import { cn } from '@/lib/cn';
import { Tooltip } from '@/components/ui';

const tone = {
  ok: 'bg-accent-soft text-accent',
  warn: 'bg-warn-soft text-warn',
  stop: 'bg-bad-soft text-bad',
} as const;

function Dot({ status, live }: { status: StepEvent['status']; live?: boolean }) {
  const Icon = status === 'ok' ? Check : status === 'warn' ? AlertTriangle : OctagonX;
  return (
    <span className={cn('relative z-10 grid h-6 w-6 shrink-0 place-items-center rounded-full', tone[status])}>
      {live ? <span className="h-2 w-2 animate-pulse-dot rounded-full bg-current" /> : <Icon className="h-3.5 w-3.5" aria-hidden />}
    </span>
  );
}

/** Timeline of pipeline steps. `live` animates the last one while the stream is open. */
export function StepList({ steps, live, detail }: { steps: StepEvent[]; live?: boolean; detail?: boolean }) {
  return (
    <ol className="relative">
      {steps.map((s, i) => {
        const last = i === steps.length - 1;
        return (
          <li key={i} className={cn('relative flex gap-3 pb-3 last:pb-0', i > 0 && 'animate-fade-up')}>
            {!last && <span aria-hidden className="absolute left-3 top-6 -ml-px h-full w-0.5 bg-border" />}
            {live && last ? <Dot status="ok" live /> : <Dot status={s.status} />}
            <div className="min-w-0 flex-1 pt-px">
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-[0.9rem] font-medium leading-snug">{s.title}</span>
                <span className="shrink-0 font-mono text-[0.72rem] tabular-nums text-muted">{s.ms ? fmtMs(s.ms) : ''}</span>
              </div>
              <div className="label-mono !text-[0.64rem]">{s.stage}</div>
              {detail && s.detail && <p className="mt-0.5 whitespace-pre-line text-[0.82rem] leading-relaxed text-muted">{s.detail}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/** Live trace while streaming: a compact card that grows one row per step. */
export function LiveTrace({ steps, label = 'Working' }: { steps: StepEvent[]; label?: string }) {
  return (
    <div className="card p-4" role="status" aria-live="polite">
      <div className="label-mono mb-3 flex items-center gap-2 !text-accent">
        <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-accent" />
        {label}
      </div>
      {steps.length ? (
        <StepList steps={steps} live />
      ) : (
        <p className="text-sm text-muted">Starting the pipeline…</p>
      )}
    </div>
  );
}

/** Collapsible "How this answer was made". */
export function TraceDisclosure({ steps, ms }: { steps: StepEvent[]; ms?: number }) {
  const [open, setOpen] = useState(false);
  if (!steps.length) return null;
  return (
    <div className="rounded-xl border border-border">
      <Tooltip tip="answer.trace">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex min-h-[44px] w-full items-center justify-between gap-3 rounded-xl px-3.5 text-left text-sm font-medium hover:bg-surface2"
      >
        <span>
          How this answer was made
          <span className="ml-2 font-mono text-xs font-normal text-muted">
            {steps.length} steps{ms ? ` · ${fmtMs(ms)}` : ''}
          </span>
        </span>
        <ChevronDown className={cn('h-4 w-4 shrink-0 text-muted transition-transform', open && 'rotate-180')} aria-hidden />
      </button>
      </Tooltip>
      {open && (
        <div className="border-t border-border px-3.5 py-3.5">
          <StepList steps={steps} detail />
        </div>
      )}
    </div>
  );
}
