/** Landing copy and the one switch between its two states (PRD 4.L, OQ-1).
 *
 * `public` is the recorded user decision (PRD 6.2a: OQ-1 = C, fully public). `pilot` is kept so the page can be
 * switched back without a rewrite: no "your textbooks" claim, a "Research pilot" label, a gate-matching CTA.
 * Copy rules: second person, short sentences, student words, no superlatives, no clinical-use claims, no latency
 * claim, no passage text. Every number comes from facts.ts, never from here. */

export type LandingMode = 'pilot' | 'public';
export const LANDING_MODE: LandingMode = 'public';

const MODES = {
  public: {
    label: null as string | null,
    headline: 'Your MBBS textbooks, answering back.',
    sub: 'Ask a question. Get the answer with the book, chapter and page, or a plain "the books don\'t settle this".',
    cta: 'Ask your first question',
  },
  pilot: {
    label: 'Research pilot',
    headline: 'Ask. Get the page.',
    sub: 'A cite-or-decline study pilot for MBBS: every answer points to the book, chapter and page, or says the books don\'t settle it.',
    cta: 'Join the pilot',
  },
} as const;

export const MODE_COPY = MODES[LANDING_MODE];

/** "2026-11-15" -> "15 Nov 2026" (fixed locale so server and client render the same text). */
function fmtDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  const mon = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][Number(m[2]) - 1];
  return `${Number(m[3])} ${mon} ${m[1]}`;
}

export const COPY = {
  heroKicker: 'A real answer, with its pages',
  howLink: 'See how it works',
  why: {
    kicker: 'Why was I wrong?',
    title: 'Got an MCQ wrong? See why, with the page.',
    body: 'Paste the question and options, mark what you picked. You get the correct option, why yours fell short, and three viva questions to test yourself.',
    cta: 'Try it with your own MCQ',
  },
  decline: {
    kicker: 'The honest no',
    title: 'It would rather say no than guess.',
    // Data-backed only: the pipeline declines when the indexed books don't settle a question. It has no per-book
    // "this book is missing" detection, so the copy must not imply one (the capture tried two not-yet subjects that
    // were answered from other books before one declined; public/landing/declined.json candidates_tried).
    body: "When the books in the library don't settle a question, it says so instead of guessing. Check the coverage list above for subjects not yet covered.",
    card: "The books don't settle this.",
    caption: (date: string) => `A real decline, captured ${fmtDate(date)}`,
  },
  body: {
    kicker: 'Body and books, linked',
    title: 'Answers know where things are.',
    body: 'Jump from a sentence to the structure in 3D. The 3D chiasm here comes from the same BodyParts3D model the Atlas opens.',
    staticCaption: 'Schematic, not the 3D model.',
    cta: 'View in 3D',
  },
  more: {
    kicker: 'Make it yours',
    title: 'Turn an answer into a flowchart. Find a lecture on the same topic.',
    videoNote: 'Suggested lectures (external, not checked by MedEvolv)',
  },
  measured: {
    kicker: "What we've measured so far",
    cta: "Start with a topic you're revising this week.",
  },
} as const;
