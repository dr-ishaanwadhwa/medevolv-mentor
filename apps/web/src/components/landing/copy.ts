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
    body: 'If your book is not in the library yet, it tells you. A study aid you can trust is one that knows where its books end.',
    card: "The books don't settle this.",
  },
  body: {
    kicker: 'Body and books, linked',
    title: 'Answers know where things are.',
    body: 'Jump from a sentence to the structure in 3D. The model below is the same one the Atlas opens.',
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
