import { create } from 'zustand';
import { streamWhy, type StepEvent, type VerdictEvent } from '@/lib/api';

export interface WhyForm {
  question: string;
  options: string[];
  chosen: number;
}
export interface WhyRun {
  phase: 'idle' | 'streaming' | 'done' | 'error';
  submitted?: WhyForm;
  steps: StepEvent[];
  verdict?: VerdictEvent;
  error?: string;
  ms?: number;
  shareId?: string;
}

interface WhyState {
  form: WhyForm;
  run: WhyRun;
  setForm: (p: Partial<WhyForm>) => void;
  setOption: (i: number, v: string) => void;
  addOption: () => void;
  removeOption: (i: number) => void;
  prefill: () => void;
  submit: () => void;
  reset: () => void;
  edit: () => void;
  setShareId: (id: string) => void;
}

export const EXAMPLE: WhyForm = {
  question:
    'A 38-year-old woman with episodic headache, sweating and palpitations is diagnosed with pheochromocytoma and is posted for surgery. Which drug should be started first?',
  options: ['Propranolol', 'Phenoxybenzamine', 'Furosemide', 'Atropine'],
  chosen: 0,
};

const blank: WhyForm = { question: '', options: ['', '', '', ''], chosen: -1 };
let ctl: AbortController | null = null;

export const useWhy = create<WhyState>((set, get) => ({
  form: blank,
  run: { phase: 'idle', steps: [] },
  setForm: (p) => set((s) => ({ form: { ...s.form, ...p } })),
  setOption: (i, v) => set((s) => ({ form: { ...s.form, options: s.form.options.map((o, j) => (j === i ? v : o)) } })),
  addOption: () => set((s) => (s.form.options.length >= 6 ? s : { form: { ...s.form, options: [...s.form.options, ''] } })),
  removeOption: (i) =>
    set((s) => {
      if (s.form.options.length <= 2) return s;
      const options = s.form.options.filter((_, j) => j !== i);
      const c = s.form.chosen;
      return { form: { ...s.form, options, chosen: c === i ? -1 : c > i ? c - 1 : c } };
    }),
  prefill: () => set({ form: { ...EXAMPLE, options: [...EXAMPLE.options] } }),
  reset: () => {
    ctl?.abort();
    set({ form: blank, run: { phase: 'idle', steps: [] } });
  },
  edit: () => {
    ctl?.abort();
    set((s) => ({ form: s.run.submitted ?? s.form, run: { phase: 'idle', steps: [] } }));
  },
  setShareId: (id) => set((s) => ({ run: { ...s.run, shareId: id } })),
  submit: () => {
    const f = get().form;
    const options = f.options.map((o) => o.trim());
    if (!f.question.trim() || options.some((o) => !o) || f.chosen < 0 || f.chosen >= options.length || get().run.phase === 'streaming') return;
    const sub: WhyForm = { question: f.question.trim(), options, chosen: f.chosen };
    ctl?.abort();
    const mine = new AbortController();
    ctl = mine;
    set({ run: { phase: 'streaming', submitted: sub, steps: [] } });
    let finished = false;
    const upd = (p: Partial<WhyRun> | ((r: WhyRun) => Partial<WhyRun>)) =>
      set((s) => ({ run: { ...s.run, ...(typeof p === 'function' ? p(s.run) : p) } }));
    void streamWhy(
      sub,
      {
        onEvent: (event, data) => {
          if (mine.signal.aborted) return;
          if (event === 'step') upd((r) => ({ steps: [...r.steps, data as StepEvent] }));
          else if (event === 'verdict') upd({ verdict: data as VerdictEvent });
          else if (event === 'done') {
            finished = true;
            upd({ phase: 'done', ms: (data as { ms: number }).ms });
          } else if (event === 'error') {
            finished = true;
            upd({ phase: 'error', error: (data as { message: string }).message });
          }
        },
        onFail: (e) => {
          finished = true;
          upd({ phase: 'error', error: e.message || 'Could not reach the server.' });
        },
        onClose: () => {
          if (!finished && !mine.signal.aborted)
            upd((r) => (r.verdict ? { phase: 'done' } : { phase: 'error', error: 'The connection closed before a verdict arrived.' }));
        },
      },
      mine.signal,
    );
  },
}));
