import type { Tip } from './types';

/** "Why was I wrong?" flow. Owner: WS-K. */
export const WHY_TIPS = {
  'why.example': { purpose: 'Fills the form with a sample question.', effect: 'Replaces what you typed so far.' },
  'why.pick': { purpose: 'Marks the option you chose in the exam.', effect: 'The explanation compares it with the correct answer.' },
  'why.remove': { purpose: 'Takes this option out of the list.', effect: 'Your pick moves if it was after this option.' },
  'why.addOption': { purpose: 'Adds another answer choice, up to six.', effect: 'A new empty option appears below.' },
  'why.submit': {
    purpose: 'Explains the correct answer and why your pick fell short.',
    effect: 'Answers from the textbooks, with citations.',
    disabled: 'Add the question, fill every option and mark your pick first.',
  },
  'why.edit': { purpose: 'Changes the question you sent.', effect: 'Returns to the form with your text filled in.' },
  'why.new': { purpose: 'Starts again with a different question.', effect: 'Clears this explanation and the form.' },
  'why.verdict.ask': { purpose: 'Asks the underlying concept as a plain question.', effect: 'Opens Ask with the question filled in.' },
  'why.verdict.explore': { purpose: 'Finds concepts related to this question.', effect: 'Opens Explore with a search for it.' },
  'why.verdict.explain': { purpose: 'Shows the concept behind the correct option.', effect: 'Opens its page in Explore.' },
  'why.verdict.viva': { purpose: 'A follow-up question to practise.', effect: 'Opens Ask with it filled in.' },
} as const satisfies Record<string, Tip>;
