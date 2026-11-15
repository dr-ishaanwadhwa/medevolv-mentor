import type { Tip } from './types';

/** Explore (concept search and concept pages). Owner: WS-K. */
export const EXPLORE_TIPS = {
  'explore.back': { purpose: 'Returns to the previous page.', effect: 'Opens concept search if you arrived by a direct link.' },
  'explore.retry': { purpose: 'Asks the service again.', effect: 'Reloads this concept.' },
  'explore.search': { purpose: 'Looks up another concept.', effect: 'Opens concept search.' },
  'explore.link': { purpose: 'A concept linked to this one in the textbook graph.', effect: 'Opens that concept.' },
  'explore.more': { purpose: 'Controls how many linked concepts are listed.', effect: 'Shows the rest, or collapses the list again.' },
  'explore.hub': { purpose: 'A wider topic this concept belongs to.', effect: 'Searches Explore for that topic.' },
  'explore.sections': { purpose: 'Controls how many book sections are listed.', effect: 'Shows every section, or only the top few.' },
  'explore.seeAlso.toggle': { purpose: 'Concepts the books mention near this one. Not verified relations.', effect: 'Shows or hides the list.' },
  'explore.seeAlso.item': { purpose: 'A concept mentioned near this one in the books.', effect: 'Opens that concept.' },
  'explore.clear': { purpose: 'Empties the search box.', effect: 'Puts the cursor back in it.' },
  'explore.filter': { purpose: 'Narrows results to one kind of concept.', effect: 'Pick All to see every kind again.' },
  'explore.result': { purpose: 'A concept that matches your search.', effect: 'Opens its page.' },
  'explore.suggested': { purpose: 'A good concept to start from.', effect: 'Opens its page.' },
  'explore.in3d': { purpose: 'Shows where this sits in the body.', effect: 'Opens the 3D atlas on it. Navigation only.' },
} as const satisfies Record<string, Tip>;
