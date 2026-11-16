'use client';

import { useEffect, useState } from 'react';
import { SearchX } from 'lucide-react';
import { LinkButton, Markdown, SkeletonLines, StatusPill, statusMeta } from '@/components/ui';
import { VerdictCard } from '@/components/why/VerdictCard';
import { getAnswer, getDiagram, type AnswerRecord, type ChatPayload, type DiagramResponse, type WhyPayload } from '@/lib/api';
import { askHref } from '@/lib/related';
import { ANSWER_TIPS as T } from '@/lib/tips/answer';
import { SpatialChips } from './AnswerCard';
import { ReadyDiagram } from './DiagramSlot';
import { RelatedTopics } from './RelatedTopics';
import { Videos } from './Videos';
import { SourceDrawer } from './SourceDrawer';
import { SourceList } from './SourceList';

type State = { s: 'loading' } | { s: 'missing' } | { s: 'error' } | { s: 'ok'; rec: AnswerRecord };

export function SharedAnswer({ id }: { id: string }) {
  const [st, setSt] = useState<State>({ s: 'loading' });
  const [src, setSrc] = useState<number | null>(null);
  const [diagram, setDiagram] = useState<DiagramResponse | null>(null);

  // A stored, server-issued flowchart, read-only; dropped silently when missing, expired or switched off (PRD 4.1).
  const diagramId = st.s === 'ok' && st.rec.kind === 'chat' ? (st.rec.payload as Partial<ChatPayload>).diagram_id : null;
  useEffect(() => {
    if (!diagramId) return;
    let live = true;
    void getDiagram(diagramId).then((d) => live && setDiagram(d));
    return () => {
      live = false;
    };
  }, [diagramId]);

  useEffect(() => {
    let live = true;
    getAnswer(id)
      .then((rec) => live && setSt({ s: 'ok', rec }))
      .catch((e: Error) => live && setSt(/\(404\)/.test(e.message) ? { s: 'missing' } : { s: 'error' }));
    return () => {
      live = false;
    };
  }, [id]);

  if (st.s === 'loading')
    return (
      <div className="card p-5">
        <SkeletonLines lines={5} />
      </div>
    );
  if (st.s !== 'ok')
    return (
      <div className="card flex flex-col items-start gap-3 p-6">
        <SearchX className="h-6 w-6 text-muted" aria-hidden />
        <h2 className="text-lg font-semibold">{st.s === 'missing' ? 'This shared answer was not found' : 'Could not load this answer'}</h2>
        <p className="text-sm text-muted">
          {st.s === 'missing' ? 'The link may be mistyped or the answer may have been removed.' : 'Check your connection and try again.'}
        </p>
      </div>
    );

  const { rec } = st;
  const p = rec.payload as Partial<ChatPayload & WhyPayload>;

  if (rec.kind === 'why' && p.verdict && p.options) {
    return (
      <>
        <div className="label-mono mb-2">Question</div>
        <p className="mb-4 text-lg font-medium leading-snug">{rec.question}</p>
        <VerdictCard v={p.verdict} sub={{ question: rec.question, options: p.options, chosen: p.chosen ?? -1 }} onOpenSource={setSrc} readOnly />
        <SourceDrawer citations={p.verdict.citations} active={src} onClose={() => setSrc(null)} />
      </>
    );
  }

  if (rec.kind === 'chat' && p.answer) {
    const a = p.answer;
    const meta = statusMeta(a.status);
    return (
      <>
        <div className="label-mono mb-2">Question</div>
        <p className="mb-4 text-lg font-medium leading-snug">{rec.question}</p>
        <article className="card space-y-4 p-4 sm:p-5">
          <StatusPill tone={meta.tone}>{meta.label}</StatusPill>
          <Markdown text={a.text} onCite={setSrc} />
          <SourceList citations={a.citations} onOpen={setSrc} />
          <SpatialChips actions={p.spatial ?? []} />
          {!meta.declined && <RelatedTopics related={p.related} hrefFor={askHref} />}
          {diagram && <ReadyDiagram diagram={diagram} citations={a.citations} onOpenSource={setSrc} />}
        </article>
        {/* Videos are fetched live from the stored topic label; the share never stores YouTube data (V-12). */}
        {!meta.declined && <div className="mt-3"><Videos topic={p.topic} /></div>}
        <SourceDrawer citations={a.citations} active={src} onClose={() => setSrc(null)} />
      </>
    );
  }

  return <p className="text-sm text-muted">This shared answer is in a format this page does not recognise.</p>;
}

export function AskYourOwn() {
  return (
    <div className="card mt-8 flex flex-col items-start gap-3 bg-accent-soft/50 p-5 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <div className="font-semibold">Ask your own question</div>
        <p className="text-sm text-muted">Answers cite the book, chapter and page, or decline.</p>
      </div>
      <LinkButton href="/ask" variant="primary" tip={T['answer.shared.ask']}>
        Open MedEvolv Mentor
      </LinkButton>
    </div>
  );
}
