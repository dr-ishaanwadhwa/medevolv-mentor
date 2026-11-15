import { create } from 'zustand';
import { streamChat, type AnswerEvent, type SpatialAction, type StepEvent } from '@/lib/api';

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
          else if (event === 'done') {
            finished = true;
            patch(id, { phase: 'done', ms: (data as { ms: number }).ms });
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
    setDraft: (draft) => set({ draft }),
    patch,
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
      patch(id, { steps: [], answer: undefined, spatial: [], phase: 'streaming', error: undefined, ms: undefined, shareId: undefined });
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
