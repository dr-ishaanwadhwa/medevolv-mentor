'use client';

import { Box } from 'lucide-react';
import { Chip, Markdown, SkeletonLines, StatusPill, Tag, statusMeta } from '@/components/ui';
import { saveAnswer, type AnswerEvent, type SpatialAction } from '@/lib/api';
import { atlasHref } from '@/lib/format';
import { useChat, type Turn } from '@/store/chat';
import { FeedbackButton, ShareButton } from './Actions';
import { ErrorCard, NextSteps } from './Cards';
import { DiagramSlot, FlowchartChip } from './DiagramSlot';
import { RelatedTopics } from './RelatedTopics';
import { SourceList } from './SourceList';
import { LiveTrace, TraceDisclosure } from './StepTrace';
import { Videos } from './Videos';

const ROUTE: Record<string, string> = {
  graph: 'Clinical case · graph route',
  case: 'Long case · focused look-ups',
  decompose: 'Compound · split into parts',
  single: 'Single question · direct search',
  refused: 'Refused before search',
};

export function SpatialChips({ actions }: { actions: SpatialAction[] }) {
  const usable = actions.filter((a) => a.fma_ids.length);
  if (!usable.length) return null;
  return (
    <div>
      <div className="label-mono mb-2 flex items-center gap-2">
        View in 3D <Tag>navigation only</Tag>
      </div>
      <div className="flex flex-wrap gap-2">
        {usable.map((a) => (
          <Chip
            key={a.fma_ids.join()}
            href={atlasHref(a.fma_ids)}
            tip={{ purpose: `Shows ${a.label} in the 3D atlas.`, effect: 'Opens the atlas at that structure.' }}
          >
            <Box className="h-4 w-4 text-accent" aria-hidden />
            {a.label}
          </Chip>
        ))}
      </div>
      <p className="mt-1.5 text-xs text-muted">Opens the 3D atlas at the structure. It locates anatomy; it is not a clinical claim.</p>
    </div>
  );
}

export function AnswerBody({ a, onOpenSource }: { a: AnswerEvent; onOpenSource: (n: number) => void }) {
  return <Markdown text={a.text} onCite={onOpenSource} />;
}

export function AnswerCard({ turn, onOpenSource }: { turn: Turn; onOpenSource: (turnId: string, n: number) => void }) {
  const { retry, setDraft, ask, patch, busy } = useChat();
  const a = turn.answer;
  const meta = a ? statusMeta(a.status) : null;

  if (turn.phase === 'error' && !a) return <ErrorCard message={turn.error} onRetry={busy ? undefined : () => retry(turn.id)} />;

  if (!a) {
    return (
      <div className="space-y-3" aria-busy="true">
        <LiveTrace steps={turn.steps} />
        <div className="card p-4">
          <SkeletonLines lines={4} />
        </div>
      </div>
    );
  }

  const open = (n: number) => onOpenSource(turn.id, n);
  const refusal = a.status === 'personal_refusal';

  return (
    <div className="space-y-3">
      {turn.phase === 'streaming' && <LiveTrace steps={turn.steps} label="Finishing" />}
      <article
        id={`ans-${turn.id}`}
        className={`card scroll-mt-16 animate-fade-up space-y-4 p-4 sm:p-5 ${meta?.declined ? (refusal ? 'border-l-4 border-l-bad' : 'border-l-4 border-l-warn') : ''}`}
      >
        <div className="flex flex-wrap items-center gap-2">
          {meta && <StatusPill tone={meta.tone}>{meta.label}</StatusPill>}
          {ROUTE[a.route] && <StatusPill tone="info">{ROUTE[a.route]}</StatusPill>}
        </div>

        {meta?.declined && a.status !== 'personal_refusal' && (
          <h3 className="text-lg font-semibold leading-snug">
            {a.status === 'insufficient' ? "The books don't settle this." : 'This is not in the textbooks I search.'}
          </h3>
        )}
        <AnswerBody a={a} onOpenSource={open} />

        {meta?.declined && (
          <NextSteps
            kind={refusal ? 'personal_refusal' : 'decline'}
            onEdit={() => {
              setDraft(turn.question);
              document.getElementById('composer')?.focus();
            }}
            onPick={(q) => ask(q)}
          />
        )}

        {a.citations.length > 0 && a.status !== 'not_in_sources' && <SourceList citations={a.citations} onOpen={open} />}
        <SpatialChips actions={turn.spatial} />
        {!meta?.declined && <RelatedTopics related={turn.related} onAsk={ask} disabled={busy} />}
        <DiagramSlot turnId={turn.id} answer={a} diagram={turn.diagram} subject={turn.topic} onOpenSource={open} />
        {turn.phase === 'done' && <TraceDisclosure steps={turn.steps} ms={turn.ms} />}

        {turn.phase === 'done' && (
          <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
            <ShareButton
              shareId={turn.shareId}
              onShare={async () => {
                // The share keeps the topic label, related topics and a server-issued diagram id; never video data.
                const id = await saveAnswer('chat', turn.question, {
                  answer: a,
                  spatial: turn.spatial,
                  topic: turn.topic ?? null,
                  related: turn.related ?? [],
                  diagram_id: turn.diagram?.s === 'ok' ? turn.diagram.d.diagram_id : null,
                });
                patch(turn.id, { shareId: id });
                return id;
              }}
            />
            <FlowchartChip turnId={turn.id} answer={a} diagram={turn.diagram} />
            <FeedbackButton question={turn.question} answerId={turn.shareId} />
          </div>
        )}
      </article>
      {turn.phase === 'done' && !meta?.declined && <Videos topic={turn.topic} />}
      {turn.phase === 'error' && <ErrorCard message={turn.error} onRetry={busy ? undefined : () => retry(turn.id)} />}
    </div>
  );
}
