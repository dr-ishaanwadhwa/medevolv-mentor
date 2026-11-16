import { create } from 'zustand';
// Relative imports keep this store loadable by the unit runner (no `@/` alias there yet).
import {
  requestDiagram,
  streamChat,
  type AnswerEvent,
  type DiagramResponse,
  type RelatedTopic,
  type SpatialAction,
  type StepEvent,
  type TopicEvent,
} from '../lib/api';

/** Flowchart state of one answer (PRD 4.1). `failed` keeps the request outcome for the copy map. */
export type DiagramState =
  | { s: 'loading' }
  | { s: 'ok'; d: DiagramResponse }
  | { s: 'failed'; result: Exclude<Awaited<ReturnType<typeof requestDiagram>>, { kind: 'ok' }> };

/** `mm_asked` (PRD D-5): set once the browser's first answer finishes, read by the landing's middleware. Value 1, no id. */
export const ASKED_COOKIE = 'mm_asked';
export function markAsked(doc: { cookie: string } | undefined = typeof document === 'undefined' ? undefined : document) {
  if (!doc || /(?:^|;\s*)mm_asked=1/.test(doc.cookie)) return;
  doc.cookie = `${ASKED_COOKIE}=1; Path=/; Max-Age=31536000; SameSite=Lax`;
}

export interface Turn {
  id: string;
  question: string;
  steps: StepEvent[];
  answer?: AnswerEvent;
  spatial: SpatialAction[];
  phase: 'streaming' | 'done' | 'error';
  error?: string;
  ms?: number;
  shareId?: string;
  /** From the `topic` event: a structured label (null for declined or patient-scoped answers) and certified links. */
  topic?: string | null;
  related?: RelatedTopic[];
  diagram?: DiagramState;
}

interface ChatState {
  turns: Turn[];
  busy: boolean;
  draft: string;
  setDraft: (d: string) => void;
  ask: (question: string) => void;
  retry: (id: string) => void;
  stop: () => void;
  clear: () => void;
  patch: (id: string, p: Partial<Turn>) => void;
  /** POST /api/diagram for this turn's answer. Ignored while one is loading (D-2). */
  drawDiagram: (id: string) => void;
  /** Page-load-wide flowchart state: `paused` after a `budget` decline, `off` after a 503 (UX table, R1). */
  diagramPaused: boolean;
  diagramOff: boolean;
  /** Epoch ms until which the chip waits after a 429. */
  diagramCooldownUntil: number;
  setDiagramPage: (p: Partial<Pick<ChatState, 'diagramPaused' | 'diagramOff' | 'diagramCooldownUntil'>>) => void;
}

let ctl: AbortController | null = null;
let seq = 0;

export const useChat = create<ChatState>((set, get) => {
  const patch = (id: string, p: Partial<Turn> | ((t: Turn) => Partial<Turn>)) =>
    set((s) => ({ turns: s.turns.map((t) => (t.id === id ? { ...t, ...(typeof p === 'function' ? p(t) : p) } : t)) }));

  function run(id: string, question: string) {
    ctl?.abort();
    const mine = new AbortController();
    ctl = mine;
    set({ busy: true });
    let finished = false;
    void streamChat(
      question,
      {
        onEvent: (event, data) => {
          if (mine.signal.aborted) return;
          if (event === 'step') patch(id, (t) => ({ steps: [...t.steps, data as StepEvent] }));
          else if (event === 'answer') patch(id, { answer: data as AnswerEvent });
          else if (event === 'spatial') patch(id, { spatial: (data as { actions: SpatialAction[] }).actions });
          else if (event === 'topic') {
            const tp = data as TopicEvent;
            patch(id, { topic: tp.topic ?? null, related: tp.topic ? (tp.related ?? []).filter((r) => r.tier === 'certified').slice(0, 6) : [] });
          } else if (event === 'done') {
            finished = true;
            patch(id, { phase: 'done', ms: (data as { ms: number }).ms });
            if (get().turns.find((t) => t.id === id)?.answer) markAsked();
          } else if (event === 'error') {
            finished = true;
            patch(id, { phase: 'error', error: (data as { message: string }).message });
          }
        },
        onFail: (e) => {
          finished = true;
          patch(id, { phase: 'error', error: e.message || 'Could not reach the server.' });
        },
        onClose: () => {
          if (ctl === mine) set({ busy: false });
          if (!finished && !mine.signal.aborted) {
            // stream ended without done: keep an answer if we have one
            patch(id, (t) => (t.answer ? { phase: 'done' } : { phase: 'error', error: 'The connection closed before an answer arrived.' }));
          }
        },
      },
      mine.signal,
    );
  }

  return {
    turns: [],
    busy: false,
    draft: '',
    diagramPaused: false,
    diagramOff: false,
    diagramCooldownUntil: 0,
    setDiagramPage: (p) => set(p),
    setDraft: (draft) => set({ draft }),
    patch,
    drawDiagram: (id) => {
      const t = get().turns.find((x) => x.id === id);
      if (!t?.answer?.answer_sig || t.diagram?.s === 'loading' || t.diagram?.s === 'ok') return;
      patch(id, { diagram: { s: 'loading' } });
      void requestDiagram(t.question, t.answer).then((r) => {
        if (r.kind === 'ok') {
          // A share made before the diagram would not include it: the next Share creates a new one (PRD 4.1).
          patch(id, { diagram: { s: 'ok', d: r.diagram }, shareId: undefined });
          return;
        }
        if (r.kind === 'declined' && r.reason === 'budget') set({ diagramPaused: true });
        if (r.kind === 'http' && r.status === 503) set({ diagramOff: true });
        if (r.kind === 'http' && r.status === 429) set({ diagramCooldownUntil: Date.now() + 60_000 });
        if (r.kind === 'http' && r.status === 403) console.warn('Flowchart: the answer signature was not accepted.');
        patch(id, { diagram: { s: 'failed', result: r } });
      });
    },
    ask: (question) => {
      const q = question.trim();
      if (!q || get().busy) return;
      const id = `t${Date.now()}-${++seq}`;
      set((s) => ({ draft: '', turns: [...s.turns, { id, question: q, steps: [], spatial: [], phase: 'streaming' }] }));
      run(id, q);
    },
    retry: (id) => {
      const t = get().turns.find((x) => x.id === id);
      if (!t || get().busy) return;
      patch(id, {
        steps: [],
        answer: undefined,
        spatial: [],
        phase: 'streaming',
        error: undefined,
        ms: undefined,
        shareId: undefined,
        topic: undefined,
        related: undefined,
        diagram: undefined,
      });
      run(id, t.question);
    },
    stop: () => {
      ctl?.abort();
      ctl = null;
      set((s) => ({
        busy: false,
        turns: s.turns.map((t) => (t.phase === 'streaming' ? { ...t, phase: t.answer ? 'done' : 'error', error: t.answer ? undefined : 'Stopped.' } : t)),
      }));
    },
    clear: () => {
      ctl?.abort();
      ctl = null;
      set({ turns: [], busy: false });
    },
  };
});
