import raw from '@/content/narration.json';

export const CHAPTER_IDS = ['library', 'books', 'guard', 'route', 'search', 'floor', 'evidence', 'cite', 'atlas', 'measured'] as const;
export type ChapterId = (typeof CHAPTER_IDS)[number];
export interface Chapter {
  id: ChapterId;
  kicker: string;
  title: string;
  body: string;
  onscreen: string;
}

/** Short rail labels. */
export const RAIL_LABELS: Record<ChapterId, string> = {
  library: 'Library', books: 'Books', guard: 'Guard', route: 'Route', search: 'Search',
  floor: 'Floor', evidence: 'Evidence', cite: 'Cite', atlas: 'Atlas', measured: 'Measured',
};

// Used only for a chapter missing from narration.json.
const FALLBACK: Record<ChapterId, Omit<Chapter, 'id'>> = {
  library: { kicker: 'One dot, one passage', title: 'Seven textbooks, in one view', body: 'Each dot is one passage from seven standard MBBS textbooks. Passages about similar things sit close together.', onscreen: 'Each dot is one passage, coloured by textbook' },
  books: { kicker: 'Seven books, one map', title: 'Why the dots split into clusters', body: 'Each cluster is one book.', onscreen: 'The dots separate into seven labelled clusters' },
  guard: { kicker: 'Study aid only', title: 'Why one question gets through', body: 'A study question passes the ring. A request for a real person’s dose is refused before any search.', onscreen: 'A question passes the ring while another bounces off' },
  route: { kicker: 'One question, two parts', title: 'Why the question splits', body: 'A compound question is split into sub-questions, each searched separately.', onscreen: 'The question splits into points heading into the library' },
  search: { kicker: 'Closest matches', title: 'How a sub-question finds passages', body: 'Each sub-question is compared with every passage.', onscreen: 'Beams link each sub-question to its nearest dots' },
  floor: { kicker: 'Off-topic questions', title: 'When the app says it doesn’t know', body: 'If the best match is below the cut-off, the language model is never called.', onscreen: 'Nearby dots stay dark outside the cut-off shell' },
  evidence: { kicker: 'Evidence first', title: 'Passages, numbered and cited', body: 'The passages sent to the model become numbered cards.', onscreen: 'Dots lift out of the library and become numbered cards' },
  cite: { kicker: 'Cited, then checked', title: 'Which cards the answer used', body: 'Each number in the answer links to its card. Cards not cited stay grey.', onscreen: 'Lines link each cited number to its card' },
  atlas: { kicker: 'Anatomy in 3D', title: 'Where the structure sits', body: 'The 3D model locates a structure. It is navigation only.', onscreen: 'The optic chiasm appears and slowly turns' },
  measured: { kicker: 'Test results', title: 'What the counters show', body: 'Results on our own question sets, not a clinical-safety guarantee.', onscreen: 'Three counters climb' },
};

export const CHAPTERS: Chapter[] = CHAPTER_IDS.map((id) => {
  const found = (raw as { chapters?: Partial<Chapter>[] }).chapters?.find((c) => c.id === id);
  return { id, ...FALLBACK[id], ...(found ?? {}) } as Chapter;
});
