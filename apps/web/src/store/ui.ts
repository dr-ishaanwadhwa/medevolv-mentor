import { create } from 'zustand';

export interface ToastAction {
  label: string;
  onClick: () => void;
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
}

let seq = 0;

export const useUi = create<UiState>((set) => ({
  toasts: [],
  toast: (text, opts) => {
    const o: ToastOptions = typeof opts === 'number' ? { ms: opts } : (opts ?? {});
    const ms = o.ms ?? (o.action ? 6000 : 2600);
    const id = ++seq;
    set((s) => ({ toasts: [...s.toasts.slice(-2), { id, text, action: o.action }] }));
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), ms);
    return id;
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));
