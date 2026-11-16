import { create } from 'zustand';
import type { TipProp } from '@/lib/tips';

export interface ToastAction {
  label: string;
  onClick: () => void;
  /** What the action does, for example Undo after Reset view. Defaults to the generic 'shell.toast.action'. */
  tip?: TipProp;
}

interface Toast {
  id: number;
  text: string;
  action?: ToastAction;
}

export interface ToastOptions {
  /** Time on screen. Defaults to 2600 ms, or 6000 ms when there is an action (time to reach it). */
  ms?: number;
  /** An inline button, for example Undo. Clicking it runs `onClick` and dismisses the toast. */
  action?: ToastAction;
}

interface UiState {
  toasts: Toast[];
  /** `toast("Saved")`, `toast("Saved", 4000)` or `toast("Reset", { action: { label: "Undo", onClick } })`. */
  toast: (text: string, opts?: number | ToastOptions) => number;
  dismiss: (id: number) => void;
  /** Stop the dismiss timer while the pointer or focus is on the toast (WCAG 2.2.1). */
  pause: (id: number) => void;
  /** Restart it with the time that was left. */
  resume: (id: number) => void;
}

let seq = 0;
const timers = new Map<number, { handle: ReturnType<typeof setTimeout> | null; remaining: number; startedAt: number }>();

export const useUi = create<UiState>((set, get) => {
  const start = (id: number, ms: number) => {
    const handle = setTimeout(() => get().dismiss(id), ms);
    timers.set(id, { handle, remaining: ms, startedAt: Date.now() });
  };
  return {
    toasts: [],
    toast: (text, opts) => {
      const o: ToastOptions = typeof opts === 'number' ? { ms: opts } : (opts ?? {});
      const ms = o.ms ?? (o.action ? 6000 : 2600);
      const id = ++seq;
      set((s) => {
        const kept = s.toasts.slice(-2);
        for (const t of s.toasts) if (!kept.includes(t)) clear(t.id);
        return { toasts: [...kept, { id, text, action: o.action }] };
      });
      start(id, ms);
      return id;
    },
    dismiss: (id) => {
      clear(id);
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
    },
    pause: (id) => {
      const t = timers.get(id);
      if (!t || t.handle === null) return;
      clearTimeout(t.handle);
      timers.set(id, { handle: null, remaining: Math.max(0, t.remaining - (Date.now() - t.startedAt)), startedAt: 0 });
    },
    resume: (id) => {
      const t = timers.get(id);
      if (!t || t.handle !== null) return;
      // at least a moment to read it again once the pointer or focus leaves
      start(id, Math.max(t.remaining, 1500));
    },
  };
});

function clear(id: number) {
  const t = timers.get(id);
  if (t?.handle) clearTimeout(t.handle);
  timers.delete(id);
}
