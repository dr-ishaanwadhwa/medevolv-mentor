// One place for story colours. Dark mode uses additive glow (bright); light mode uses normal blending (deeper).
export const BOOK_COLORS: Record<string, { dark: string; light: string }> = {
  harrison: { dark: '#5ccfe0', light: '#0b7a88' },
  davidson: { dark: '#ff9a55', light: '#c4600f' },
  robbins: { dark: '#f2d45c', light: '#a88200' },
  guyton: { dark: '#6e9dff', light: '#2f5fd0' },
  tripathi: { dark: '#b88cff', light: '#7440d0' },
  micro: { dark: '#6fe0a2', light: '#168a55' },
  grays: { dark: '#f58bd0', light: '#bb2f8e' },
};
const EXTRA = ['#5ccfe0', '#ff9a55', '#f2d45c', '#6e9dff', '#b88cff', '#6fe0a2', '#f58bd0'];
export function bookColor(id: string, idx: number, dark: boolean): string {
  const c = BOOK_COLORS[id];
  return c ? (dark ? c.dark : c.light) : EXTRA[idx % EXTRA.length];
}
export const SUB_COLORS = {
  dark: ['#ffffff', '#ffd27a', '#c9a8ff', '#8ff0c0'],
  light: ['#0f2f38', '#a85d00', '#5b2fb8', '#0f7a4a'],
};
