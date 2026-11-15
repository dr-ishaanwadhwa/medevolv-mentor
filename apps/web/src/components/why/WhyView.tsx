'use client';

import { useEffect, useState } from 'react';
import { Pencil, RotateCcw } from 'lucide-react';
import { Button, StatusPill } from '@/components/ui';
import { ErrorCard } from '@/components/chat/Cards';
import { SourceDrawer } from '@/components/chat/SourceDrawer';
import { LiveTrace, TraceDisclosure } from '@/components/chat/StepTrace';
import { LETTERS } from '@/lib/format';
import { cn } from '@/lib/cn';
import { useWhy } from '@/store/why';
import { VerdictCard } from './VerdictCard';
import { WhyForm } from './WhyForm';

export function WhyView() {
  const { run, edit, submit, reset } = useWhy();
  const [src, setSrc] = useState<number | null>(null);
  const sub = run.submitted;

  useEffect(() => {
    if (run.phase === 'streaming') window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [run.phase]);
  useEffect(() => {
    if (run.verdict) document.getElementById('verdict')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [run.verdict]);

  return (
    <div className="page py-6 sm:py-10">
      <div className="mb-6">
        <div className="label-mono !text-accent">Wrong in a QBank or paper?</div>
        <h1 className="mt-1.5 text-[1.9rem] font-bold leading-tight tracking-tight sm:text-4xl">Why was I wrong?</h1>
        <p className="mt-2 max-w-[60ch] text-muted">
          Paste a question and the option you chose. You get the textbook verdict with book, chapter and page, or an honest
          &ldquo;the books don&apos;t settle this&rdquo;.
        </p>
      </div>

      {run.phase === 'idle' || !sub ? (
        <WhyForm />
      ) : (
        <div className="space-y-4">
          <section className="card p-4" aria-label="Your question">
            <div className="flex items-start justify-between gap-3">
              <div className="label-mono">Your question</div>
              <div className="-mr-2 -mt-2 flex">
                <Button size="sm" variant="ghost" onClick={edit}>
                  <Pencil className="h-4 w-4" /> Edit
                </Button>
                <Button size="sm" variant="ghost" onClick={reset}>
                  <RotateCcw className="h-4 w-4" /> New
                </Button>
              </div>
            </div>
            <p className="mt-1 text-[0.95rem] leading-snug">{sub.question}</p>
            <ul className="mt-3 grid gap-1.5 sm:grid-cols-2">
              {sub.options.map((o, i) => {
                const correct = run.verdict?.correct_option === i;
                return (
                  <li
                    key={i}
                    className={cn(
                      'flex items-start gap-2 rounded-lg border px-2.5 py-1.5 text-sm',
                      correct ? 'border-good bg-good-soft' : i === sub.chosen ? 'border-bad/40 bg-bad-soft/60' : 'border-border',
                    )}
                  >
                    <span className="font-mono text-xs font-semibold text-muted">{LETTERS[i]}</span>
                    <span className="min-w-0 flex-1">{o}</span>
                    {i === sub.chosen && <StatusPill tone={correct ? 'good' : 'bad'} className="!px-1.5 !py-0 !text-[0.62rem]">picked</StatusPill>}
                    {correct && i !== sub.chosen && <StatusPill tone="good" className="!px-1.5 !py-0 !text-[0.62rem]">correct</StatusPill>}
                  </li>
                );
              })}
            </ul>
          </section>

          {run.phase === 'streaming' && !run.verdict && <LiveTrace steps={run.steps} label="Checking the books" />}
          {run.phase === 'error' && !run.verdict && <ErrorCard message={run.error} onRetry={submit} />}
          {run.verdict && (
            <div id="verdict" className="scroll-mt-16 space-y-3">
              <VerdictCard v={run.verdict} sub={sub} onOpenSource={setSrc} shareId={run.shareId} />
              {run.phase === 'done' && <TraceDisclosure steps={run.steps} ms={run.ms} />}
            </div>
          )}
        </div>
      )}
      <SourceDrawer citations={run.verdict?.citations ?? []} active={src} onClose={() => setSrc(null)} />
    </div>
  );
}
