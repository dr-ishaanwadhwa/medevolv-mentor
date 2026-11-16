import journeyJson from '../../../public/landing/journey.json';
import declinedJson from '../../../public/landing/declined.json';
import whyJson from '../../../public/landing/why.json';
import { BOOK_SHORT, BOOKS, editionShort } from './facts';

/** Build-time captures of the real pipeline (scripts/build_landing_captures.py). Pointers and Mentor's own prose only:
 * the capture script drops `excerpt`, and captures.test.ts fails if one is present. */

export interface Pointer {
  index: number;
  cited: boolean;
  book: string;
  edition: string;
  chapter: string;
  pages: string;
  section_id: string;
}

export const journey = journeyJson as typeof journeyJson & { citations: Pointer[] };
export const declined = declinedJson;
export const why = whyJson as typeof whyJson & { verdict: { citations: Pointer[] } };

const bookId = (title: string) => BOOKS.find((b) => b.title === title)?.id ?? '';

/** "Harrison 22e · Ch 34 · pp 263-279" (the pointer's pages are the section's range, so it says pp). */
export function citeLabel(c: Pointer): string {
  const id = bookId(c.book);
  const name = BOOK_SHORT[id] ?? c.book;
  const ed = editionShort(c.book);
  const ch = /^\s*(\d+)/.exec(c.chapter)?.[1];
  return [ed ? `${name} ${ed}` : name, ch ? `Ch ${ch}` : c.chapter, c.pages ? `pp ${c.pages}` : ''].filter(Boolean).join(' · ');
}

/** Index in story.json `books` for each cited book, in first-cited order (drives which galaxies glow). */
export function citedBookIndexes(cites: Pointer[]): number[] {
  const out: number[] = [];
  for (const c of cites) {
    if (!c.cited) continue;
    const i = BOOKS.findIndex((b) => b.title === c.book);
    if (i >= 0 && !out.includes(i)) out.push(i);
  }
  return out;
}

export interface HeroAnswer { sentences: string[]; used: Pointer[] }

/** The first two sentences of the captured answer and the pointers they cite. */
export function heroAnswer(text: string, cites: Pointer[]): HeroAnswer {
  const body = text.split(/\n\s*\n/)[0] ?? text;
  const sentences = body.split(/(?<=\.)\s+(?=[A-Z])/).slice(0, 2);
  const nums = new Set<number>();
  for (const s of sentences) for (const m of s.matchAll(/\[(\d+)\]/g)) nums.add(Number(m[1]));
  const used = [...nums].sort((a, b) => a - b).map((n) => cites.find((c) => c.index === n)).filter((c): c is Pointer => !!c);
  return { sentences, used };
}

export const CHIASM_FMA = 'FMA62045';
