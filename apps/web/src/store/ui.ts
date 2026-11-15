import { create } from 'zustand';

interface Toast {
  id: number;
  text: string;
}

interface UiState {
  toasts: Toast[];
  toast: (text: string, ms?: number) => void;
}

let seq = 0;

export const useUi = create<UiState>((set) => ({
  toasts: [],
  toast: (text, ms = 2600) => {
    const id = ++seq;
    set((s) => ({ toasts: [...s.toasts.slice(-2), { id, text }] }));
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), ms);
  },
}));
