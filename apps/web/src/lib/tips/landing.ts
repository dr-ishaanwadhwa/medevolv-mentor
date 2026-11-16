import type { Tip } from './types';

/** Landing page controls. Owner: WS-L. */
export const LANDING_TIPS = {
  'landing.cta': { purpose: 'Starts your first question.', effect: 'Opens Ask with an empty box, ready to type.' },
  'landing.how': { purpose: 'Shows how an answer is built from the books.', effect: 'Opens the How it works walkthrough.' },
  'landing.example': { purpose: 'A sample exam-style question.', effect: 'Opens Ask and sends it, so the cited answer appears.' },
  'landing.why': { purpose: 'The wrong-MCQ explainer.', effect: 'Opens Why was I wrong? so you can paste your own question.' },
  'landing.view3d': { purpose: 'Finds the structure this answer mentions.', effect: 'Opens the 3D Atlas with the optic chiasm selected.' },
  'landing.final': { purpose: 'Starts your first question.', effect: 'Opens Ask with an empty box, ready to type.' },
  'landing.sticky': { purpose: 'Starts your first question.', effect: 'Opens Ask with an empty box, ready to type.' },
} as const satisfies Record<string, Tip>;
