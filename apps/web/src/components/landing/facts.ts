import story from '../../../public/story/story.json';

/** Every number the landing shows, with where it comes from (PRD L-7, Honesty rules).
 * A unit test asserts each fact has a source, a date and a caveat. Nothing numeric is typed into a component. */

export interface Fact {
  id: string;
  /** What is rendered. */
  value: string;
  /** What the value means, in the words shown next to it. */
  text: string;
  /** Named data or eval file the value was copied from. */
  source: string;
  /** Date of the measurement (or of the file). */
  date: string;
  /** Sample size and scope, in words. */
  sample: string;
  /** Caveat strings that must render with the number. */
  caveats: readonly string[];
}

/** Word for word from /how (components/story/Story.tsx `st-caveat`). Keep them identical. */
export const EVAL_CAVEAT =
  'Results on our own question sets, not a clinical-safety guarantee. Retrieval is not yet measured for every book. A study aid, not medical advice.';
/** Wording given in PRD 4.L scene 4. */
export const LIMITATION =
  'Hard clinical cases still fail our clinician review; do not use it for patient care.';

export const FACTS: Record<'passages' | 'books' | 'behaviour', Fact> = {
  passages: {
    id: 'passages',
    value: story.n.toLocaleString('en-US'),
    text: 'passages from seven textbooks are in the library',
    // story.json is produced by scripts/build_library_map.py from the indexed books; n is the passage count.
    source: 'apps/web/public/story/story.json (n)',
    date: '2026-11-13',
    sample: `${story.n} indexed passages, ${story.books.length} books`,
    caveats: ['Counts passages in the index, not pages.'],
  },
  books: {
    id: 'books',
    value: String(story.books.length),
    text: 'textbooks in the library',
    source: 'apps/web/public/story/story.json (books)',
    date: '2026-11-13',
    sample: `${story.books.length} books`,
    caveats: ['Biochemistry, OBG, Surgery, PSM, Forensic Medicine, ENT, Ophthalmology and Paediatrics are not covered yet.'],
  },
  behaviour: {
    id: 'behaviour',
    value: '39 of 39',
    text: 'questions got the right behaviour (answered, declined or refused) in our internal test',
    // docs/eval_2026-11-13.md section 1, "Right behaviour (answer / decline / refuse): 39 / 39".
    source: 'docs/eval_2026-11-13.md section 1',
    date: '13 Nov 2026',
    sample: '39 questions we wrote ourselves: 22 factual, 3 comparison, 5 clinical, 5 off-topic, 4 personal; internal',
    caveats: [EVAL_CAVEAT, LIMITATION],
  },
};

/** Subject coverage, grouped as the strip reads. Book ids and editions come from story.json; the subject labels are the
 * only text typed here (PRD 4.L scene 0). */
export const SUBJECT_OF: Record<string, string> = {
  grays: 'Anatomy',
  guyton: 'Physiology',
  robbins: 'Pathology',
  tripathi: 'Pharmacology',
  micro: 'Microbiology',
  davidson: 'Medicine',
  harrison: 'Medicine',
};
export const SUBJECT_ORDER = ['Anatomy', 'Physiology', 'Pathology', 'Pharmacology', 'Microbiology', 'Medicine'] as const;
/** Subjects with no book yet. The list is the PRD's own; the user confirms it at approval. */
export const NOT_YET = ['Biochemistry', 'OBG', 'Surgery', 'PSM', 'Forensic Medicine', 'ENT', 'Ophthalmology', 'Paediatrics'] as const;

export const BOOK_SHORT: Record<string, string> = {
  grays: "Gray's",
  guyton: 'Guyton',
  tripathi: 'Tripathi',
  robbins: 'Robbins',
  micro: 'Essentials of Medical Microbiology',
  davidson: 'Davidson',
  harrison: 'Harrison',
};

/** "(24th ed.)" -> "24e"; '' when the title carries no edition. */
export function editionShort(title: string): string {
  const m = /\((\d+)(?:st|nd|rd|th) ed\.\)/.exec(title);
  return m ? `${m[1]}e` : '';
}

export interface CoverageItem { id: string; name: string; edition: string }
export function coverage(): { subject: string; books: CoverageItem[] }[] {
  return SUBJECT_ORDER.map((subject) => ({
    subject,
    books: story.books
      .filter((b) => SUBJECT_OF[b.id] === subject)
      .map((b) => ({ id: b.id, name: BOOK_SHORT[b.id] ?? b.id, edition: editionShort(b.title) })),
  })).filter((g) => g.books.length);
}

export const BOOKS = story.books.map((b) => ({ id: b.id, title: b.title }));

/** Exam or viva questions, one per professional year (anatomy, pathology, medicine). None is patient-scoped. The
 * pathology and medicine ones are q11 and q22 of eval/product_questions.jsonl, answered in the 39-question internal eval
 * (docs/eval_2026-11-13.md). The anatomy one is the hero question: not in that eval set, but answered with citations in
 * the capture (public/landing/journey.json). The user approves the final three. */
export const EXAMPLES = [
  { id: 'anatomy', year: '1st year', q: 'Trace the visual pathway and the field defect from a lesion at the optic chiasm.' },
  { id: 'pathology', year: '2nd year', q: 'What are the morphological features of caseous necrosis?' },
  { id: 'medicine', year: 'Final year', q: 'Compare type 1 and type 2 diabetes mellitus.' },
] as const;

export const askHref = (q: string) => `/ask?q=${encodeURIComponent(q)}&go=1`;

/** Questions that must never appear as landing examples or heroes (PRD L-7a, safety framing). */
export const PATIENT_SCOPED = /\b(my|our)\s+(mother|father|son|daughter|wife|husband|child|baby|patient)\b|\bI\s+(have|am|take)\b|\bshould\s+I\b|a\s+patient\b|what\s+drug\s+should/i;
