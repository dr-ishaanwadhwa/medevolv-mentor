'use client';

import Link from 'next/link';
import { ArrowUpRight, Compass, Lightbulb, MessageCircleQuestion } from 'lucide-react';
import { Chip, Markdown, StatusPill } from '@/components/ui';
import { FeedbackButton, ShareButton } from '@/components/chat/Actions';
import { SourceList } from '@/components/chat/SourceList';
import { saveAnswer, type VerdictEvent } from '@/lib/api';
import { LETTERS } from '@/lib/format';
import { useWhy, type WhyForm } from '@/store/why';

const exploreHref = (q: string) => `/explore?q=${encodeURIComponent(q.slice(0, 80))}`;
const askHref = (q: string, go = true) => `/?q=${encodeURIComponent(q)}${go ? '&go=1' : ''}`;

export function VerdictCard({
  v,
  sub,
  onOpenSource,
  shareId,
  readOnly,
}: {
  v: VerdictEvent;
  sub: WhyForm;
  onOpenSource: (n: number) => void;
  shareId?: string;
  readOnly?: boolean;
}) {
  const setShareId = useWhy((s) => s.setShareId);

  if (v.status === 'insufficient' || v.correct_option == null) {
    return (
      <article className="card animate-fade-up space-y-4 border-l-4 border-l-warn p-4 sm:p-5">
        <StatusPill tone="warn">Not settled by the books</StatusPill>
        <h3 className="text-xl font-semibold leading-snug">The books don&apos;t settle this.</h3>
        <Markdown text={v.explanation || 'The retrieved passages do not let us pick a correct option, so no verdict is given.'} onCite={onOpenSource} />
        <div className="rounded-xl bg-surface2/60 p-3.5">
          <div className="label-mono mb-2">What you can do next</div>
          <ul className="mb-3 space-y-1 text-sm text-muted">
            <li>Check that the stem and every option are complete and spelled as in the source.</li>
            <li>Ask the underlying concept on its own; the books may cover it even if they do not rank these options.</li>
            <li>Treat this as a question for your teacher or a reference, not a verdict.</li>
          </ul>
          {!readOnly && (
            <div className="flex flex-wrap gap-2">
              <Chip href={askHref(sub.question, false)}>
                <MessageCircleQuestion className="h-4 w-4" /> Ask it as a concept question
              </Chip>
              <Chip href={exploreHref(sub.question)}>
                <Compass className="h-4 w-4" /> Explore related topics
              </Chip>
            </div>
          )}
        </div>
        {v.citations.length > 0 && <SourceList citations={v.citations} onOpen={onOpenSource} />}
      </article>
    );
  }

  const correct = v.correct_option;
  const right = correct === sub.chosen;
  const label = (i: number) => `${LETTERS[i]}. ${sub.options[i] ?? ''}`;

  return (
    <article className="card animate-fade-up space-y-5 p-4 sm:p-5">
      <div>
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <StatusPill tone="good">Textbook verdict</StatusPill>
          {right && <StatusPill tone="good">You picked the right one</StatusPill>}
        </div>
        <div className="label-mono">Correct answer</div>
        <h3 className="mt-1 text-[1.65rem] font-bold leading-tight tracking-tight text-accent sm:text-3xl">{label(correct)}</h3>
      </div>

      {v.chosen_wrong_because && (
        <section className={`rounded-xl p-4 ${right ? 'bg-good-soft' : 'bg-bad-soft'}`} aria-label={right ? 'Why yours is right' : 'Why yours is wrong'}>
          <div className={`label-mono !text-[0.7rem] ${right ? '!text-good' : '!text-bad'}`}>
            {right ? 'Why yours is right' : `Why yours is wrong · you picked ${label(sub.chosen)}`}
          </div>
          <Markdown text={v.chosen_wrong_because} onCite={onOpenSource} className="mt-1.5" small />
        </section>
      )}

      <section aria-label="Explanation">
        <div className="label-mono mb-1.5">Explanation, from the books</div>
        <Markdown text={v.explanation} onCite={onOpenSource} />
      </section>

      {v.citations.length > 0 && <SourceList citations={v.citations} onOpen={onOpenSource} />}

      {v.viva_questions.length > 0 && (
        <section aria-label="Viva questions">
          <div className="label-mono mb-2 flex items-center gap-1.5">
            <Lightbulb className="h-3.5 w-3.5" aria-hidden /> Viva questions to try next
          </div>
          <ul className="grid gap-2">
            {v.viva_questions.map((q) => (
              <li key={q}>
                <Link
                  href={readOnly ? askHref(q, false) : askHref(q)}
                  className="group flex min-h-[44px] items-start justify-between gap-3 rounded-xl border border-border bg-bg p-3.5 text-[0.93rem] leading-snug transition-colors hover:border-accent/50 hover:bg-accent-soft/40"
                >
                  <span>{q}</span>
                  <ArrowUpRight className="mt-0.5 h-4 w-4 shrink-0 text-muted group-hover:text-accent" aria-hidden />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
        <Chip href={exploreHref(sub.options[correct] ?? sub.question)}>
          <Compass className="h-4 w-4 text-accent" /> Explain the concept
        </Chip>
        {!readOnly && (
          <>
            <ShareButton
              shareId={shareId}
              onShare={async () => {
                const id = await saveAnswer('why', sub.question, { options: sub.options, chosen: sub.chosen, verdict: v });
                setShareId(id);
                return id;
              }}
            />
            <FeedbackButton question={sub.question} answerId={shareId} />
          </>
        )}
      </div>
    </article>
  );
}
