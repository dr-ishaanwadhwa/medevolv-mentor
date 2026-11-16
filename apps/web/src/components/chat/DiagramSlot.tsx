'use client';

/**
 * The light half of the flowchart maker (PRD 4.1): the "Flowchart" chip on the action row and the card states
 * (loading, declined, error). The renderer itself (dagre) is in Diagram.tsx and loads only after a tap (D-8).
 */
import { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { Loader2, RotateCcw, Workflow } from 'lucide-react';
import { Button, Chip, Skeleton } from '@/components/ui';
import { useFeature } from '@/components/FeaturesProvider';
import type { AnswerCitation, AnswerEvent, DiagramResponse } from '@/lib/api';
import { CHIP_LABEL, COPY, askInstead, diagramUx, loadingCopy } from '@/lib/copy/diagram';
import { maxPassageMarker, offersFlowchart } from '@/lib/diagram/graph';
import { ANSWER_TIPS as T } from '@/lib/tips/answer';
import { useChat, type DiagramState } from '@/store/chat';

const Diagram = dynamic(() => import('./Diagram'), {
  ssr: false,
  loading: () => <Skeleton className="h-64 w-full rounded-xl" />,
});

function useNow(until: number) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (until <= now) return;
    const t = window.setTimeout(() => setNow(Date.now()), until - now + 50);
    return () => window.clearTimeout(t);
  }, [until, now]);
  return now;
}

/** The chip. Absent unless the `diagram` flag is on, the answer is signed and has 3+ cited sentences (D-1, D-15, D-16). */
export function FlowchartChip({ turnId, answer, diagram }: { turnId: string; answer: AnswerEvent; diagram?: DiagramState }) {
  const on = useFeature('diagram');
  const { drawDiagram, diagramOff, diagramPaused, diagramCooldownUntil } = useChat();
  const now = useNow(diagramCooldownUntil);
  if (!on || diagramOff || !offersFlowchart(answer)) return null;
  if (diagram?.s === 'ok') return null;
  const ux = diagram?.s === 'failed' ? diagramUx(diagram.result) : null;
  if (ux?.hideChip) return null;
  const loading = diagram?.s === 'loading';
  const cooling = diagramCooldownUntil > now;
  const disabled = loading || diagramPaused || cooling;
  const reason = diagramPaused ? COPY.paused : cooling ? COPY.wait : COPY.working;
  return (
    <Button
      size="sm"
      variant="secondary"
      className="rounded-full"
      disabled={disabled}
      onClick={() => drawDiagram(turnId)}
      tip={{ ...T['answer.flowchart'], disabled: reason }}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Workflow className="h-4 w-4" aria-hidden />}
      {CHIP_LABEL}
    </Button>
  );
}

/** The card slot inside the answer article, after the sources and 3D chips, before the trace (PRD 4.1 placement). */
export function DiagramSlot({
  turnId,
  answer,
  diagram,
  subject,
  onOpenSource,
}: {
  turnId: string;
  answer: AnswerEvent;
  diagram?: DiagramState;
  subject?: string | null;
  onOpenSource: (n: number) => void;
}) {
  const { drawDiagram, ask, busy } = useChat();
  const ref = useRef<HTMLDivElement>(null);
  const loading = diagram?.s === 'loading';

  // The chip sits lower on the card: bring the skeleton into view and give it focus when loading starts.
  useEffect(() => {
    if (!loading || !ref.current) return;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    ref.current.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'center' });
    ref.current.focus({ preventScroll: true });
  }, [loading]);

  if (!diagram) return null;
  if (diagram.s === 'ok') return <ReadyDiagram diagram={diagram.d} citations={answer.citations} onOpenSource={onOpenSource} />;
  if (diagram.s === 'loading')
    return (
      <div ref={ref} tabIndex={-1} aria-busy="true" className="rounded-xl border border-border bg-surface p-3 outline-none sm:p-4">
        <p className="mb-2 text-sm text-muted" role="status">
          {loadingCopy(maxPassageMarker(answer.text))}
        </p>
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );

  const ux = diagramUx(diagram.result);
  if (!ux.copy) return null;
  const suggestion = ux.askChip ? askInstead(subject) : null;
  return (
    <div className="rounded-xl border border-border bg-surface2/60 p-3.5 text-sm text-muted" role="status">
      <p>{ux.copy}</p>
      {(ux.retry || suggestion) && (
        <div className="mt-2.5 flex flex-wrap gap-2">
          {ux.retry && (
            <Button size="sm" variant="secondary" onClick={() => drawDiagram(turnId)} tip={T['answer.flowchart.retry']}>
              <RotateCcw className="h-4 w-4" aria-hidden /> Retry
            </Button>
          )}
          {suggestion && (
            <Chip onClick={() => ask(suggestion)} disabled={busy} tip={T['answer.flowchart.askInstead']}>
              {suggestion}
            </Chip>
          )}
        </div>
      )}
    </div>
  );
}

/** A ready diagram (also used read-only on shared pages). */
export function ReadyDiagram({
  diagram,
  citations,
  onOpenSource,
}: {
  diagram: DiagramResponse;
  citations: AnswerCitation[];
  onOpenSource: (n: number) => void;
}) {
  return <Diagram diagram={diagram} citations={citations} onOpenSource={onOpenSource} />;
}
