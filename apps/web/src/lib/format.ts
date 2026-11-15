import type { AnswerCitation } from './api';

export const LETTERS = 'ABCDEF';

/** "KD Tripathi · Pharmacology, 8th ed." style one-liner location pieces. */
export function citationWhere(c: AnswerCitation) {
  return {
    book: c.edition ? `${c.book} (${c.edition})` : c.book,
    chapter: c.chapter,
    pages: c.pages ? (/[-–,]/.test(c.pages) ? `pp. ${c.pages}` : `p. ${c.pages}`) : '',
  };
}

export function clip(s: string, n: number) {
  return s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s;
}

export function fmtMs(ms: number) {
  return ms < 950 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`;
}

/** Atlas deep link from spatial actions (navigation only). */
export function atlasHref(fmaIds: string[]) {
  return `/atlas?select=${fmaIds.join(',')}`;
}

export function isRealUrlId(id: string) {
  return /^[A-Za-z0-9_-]{4,64}$/.test(id);
}
