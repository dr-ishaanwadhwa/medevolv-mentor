'use client';

import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { ArrowUpRight, Trash2 } from 'lucide-react';
import { Button, Tag } from '@/components/ui';
import { DEMO_PROMPTS } from '@/lib/demo';
import { useChat } from '@/store/chat';
import { AnswerCard } from './AnswerCard';
import { Composer } from './Composer';
import { SourceDrawer } from './SourceDrawer';

function Hero() {
  const ask = useChat((s) => s.ask);
  return (
    <div className="animate-fade-up pt-6 sm:pt-12">
      <div className="label-mono !text-accent">Textbook-grounded study companion</div>
      <h1 className="mt-2 text-[2rem] font-bold leading-[1.08] tracking-tight sm:text-[2.6rem]">
        Ask your textbooks.
        <br />
        <span className="text-muted">Get the page, or an honest no.</span>
      </h1>
      <p className="mt-4 max-w-[60ch] text-base leading-relaxed text-muted">
        Every answer is built only from seven standard MBBS textbooks and cites book, chapter and page. When the books do not
        cover a question, it says so instead of guessing.
      </p>
      <div className="mt-7 grid gap-2.5 sm:grid-cols-2">
        {DEMO_PROMPTS.map((d) => (
          <button
            key={d.text}
            type="button"
            onClick={() => ask(d.text)}
            className="card group flex min-h-[44px] flex-col items-start gap-1.5 p-4 text-left transition-colors hover:border-accent/50 hover:bg-accent-soft/40"
          >
            <span className="flex w-full items-center justify-between gap-2">
              <Tag>{d.tag}</Tag>
              <ArrowUpRight className="h-4 w-4 text-muted transition-colors group-hover:text-accent" aria-hidden />
            </span>
            <span className="text-[0.93rem] leading-snug">{d.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/** The demo prompts stay one tap away after the first answer (the hero cards disappear once a chat starts). */
function TryRow() {
  const ask = useChat((s) => s.ask);
  const streaming = useChat((s) => s.turns.some((t) => t.phase === 'streaming'));
  return (
    <div className="-mx-1 flex items-center gap-2 overflow-x-auto px-1 pb-2 [scrollbar-width:none]" aria-label="Try a demo question">
      <span className="label-mono shrink-0">Try</span>
      {DEMO_PROMPTS.map((d) => (
        <button
          key={d.text}
          type="button"
          disabled={streaming}
          title={d.text}
          onClick={() => ask(d.text)}
          className="shrink-0 rounded-full border border-border bg-surface px-3 py-1.5 text-xs text-muted transition-colors hover:border-accent/50 hover:text-ink disabled:opacity-50"
        >
          {d.tag}
        </button>
      ))}
    </div>
  );
}

/** Reads ?q=&go=1 once, then cleans the URL. */
function QueryPrefill() {
  const sp = useSearchParams();
  const done = useRef(false);
  const { setDraft, ask } = useChat();
  useEffect(() => {
    const q = sp.get('q');
    if (!q || done.current) return;
    done.current = true;
    if (sp.get('go') === '1') ask(q);
    else setDraft(q);
    window.history.replaceState(null, '', '/');
    document.getElementById('composer')?.focus();
  }, [sp, ask, setDraft]);
  return null;
}

export function ChatView() {
  const { turns, clear } = useChat();
  const [src, setSrc] = useState<{ turnId: string; n: number } | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const lastId = turns[turns.length - 1]?.id;
  const lastHasAnswer = !!turns[turns.length - 1]?.answer;

  // new question: bring the thread to the bottom; answer arrival: show the top of the answer
  useEffect(() => {
    if (lastId) bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [lastId]);
  useEffect(() => {
    if (!lastId || !lastHasAnswer) return;
    // after layout settles; instant, because a smooth scroll still heading to the bottom would swallow a smooth one
    const t = window.setTimeout(() => document.getElementById(`ans-${lastId}`)?.scrollIntoView({ behavior: 'auto', block: 'start' }), 60);
    return () => window.clearTimeout(t);
  }, [lastId, lastHasAnswer]);

  const srcTurn = useMemo(() => turns.find((t) => t.id === src?.turnId), [turns, src]);

  return (
    <div className="page flex min-h-[calc(100dvh-var(--topbar-h))] flex-col md:min-h-dvh">
      <Suspense fallback={null}>
        <QueryPrefill />
      </Suspense>
      <div className="flex-1 pb-4">
        {turns.length === 0 ? (
          <Hero />
        ) : (
          <div className="space-y-8 pt-6">
            <div className="flex justify-end">
              <Button size="sm" variant="ghost" onClick={clear}>
                <Trash2 className="h-4 w-4" /> Clear chat
              </Button>
            </div>
            {turns.map((t) => (
              <section key={t.id} aria-label="Question and answer" className="space-y-3">
                <div className="flex justify-end">
                  <p className="max-w-[88%] animate-fade-up rounded-2xl rounded-br-md bg-accent px-4 py-2.5 text-[0.97rem] leading-snug text-accent-ink">
                    {t.question}
                  </p>
                </div>
                <AnswerCard turn={t} onOpenSource={(turnId, n) => setSrc({ turnId, n })} />
              </section>
            ))}
          </div>
        )}
        <div ref={bottom} />
      </div>
      {turns.length > 0 && <TryRow />}
      <Composer />
      <SourceDrawer citations={srcTurn?.answer?.citations ?? []} active={srcTurn ? src!.n : null} onClose={() => setSrc(null)} />
    </div>
  );
}
