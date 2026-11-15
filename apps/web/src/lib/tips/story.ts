import type { Tip } from './types';

/** The /how story. Chapter dots use data tips built at the call site from the chapter title. Owner: WS-K. */
export const STORY_TIPS = {
  'story.skip': { purpose: 'Skips the animated story.', effect: 'Opens the plain text version of this page.' },
  'story.try.search': {
    purpose: 'Searches the textbooks for your question.',
    effect: 'Shows the passages found, below.',
    disabled: 'Type a question first.',
  },
  'story.try.example': { purpose: 'A sample question to try.', effect: 'Runs the search with it straight away.' },
} as const satisfies Record<string, Tip>;
