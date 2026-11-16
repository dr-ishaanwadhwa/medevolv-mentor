import type { Tip } from './types';

/** App shell, UI kit and global controls. Owner: WS-K. */
export const SHELL_TIPS = {
  // The logo opens Ask, not the landing (PRD 4.L, D-6); the landing is "Take the tour".
  'shell.logo': { purpose: 'Home for asking questions.', effect: 'Opens Ask, with your earlier answers kept.' },
  'shell.skip': { purpose: 'Lets keyboard users jump past the menu.', effect: 'Moves focus to the main content.' },
  'shell.nav.ask': { purpose: 'Ask a textbook question.', effect: 'Opens the question box. Answers carry citations.' },
  'shell.nav.why': { purpose: 'Find out why an exam option was wrong.', effect: 'Opens a form for the question, options and your pick.' },
  'shell.nav.explore': { purpose: 'Browse concepts and how they link.', effect: 'Opens concept search.' },
  'shell.nav.atlas': { purpose: 'See body structures in 3D.', effect: 'Opens the 3D atlas. For orientation, not clinical claims.' },
  'shell.nav.how': { purpose: 'How the answers are made and checked.', effect: 'Opens the walkthrough and the measured results.' },
  'shell.theme.toDark': { purpose: 'Easier on the eyes in a dark room.', effect: 'Switches the whole app to the dark theme.' },
  'shell.theme.toLight': { purpose: 'Better in bright light.', effect: 'Switches the whole app to the light theme.' },
  'shell.drawer.close': { purpose: 'Closes this panel.', effect: 'Returns you to the page underneath.' },
  'shell.error.retry': { purpose: 'Tries loading this page again.', effect: 'Re-runs the part that failed. Nothing is lost.' },
  'shell.toast.action': { purpose: 'Runs the action offered in this message.', effect: 'The message then closes.' },
  'shell.coach.dismiss': { purpose: 'Hides this hint.', effect: 'It will not appear again on this device.' },
  'shell.footer.tour': { purpose: 'A one-minute look at what Mentor does.', effect: 'Opens the front page tour.' },
  'shell.legal.credits': { purpose: 'Who made the 3D models and data.', effect: 'Opens the credits and licences.' },
  'shell.legal.privacy': { purpose: 'What is stored and sent, and where.', effect: 'Opens the privacy page.' },
  'shell.legal.terms': { purpose: 'The rules for using Mentor.', effect: 'Opens the terms page.' },
  'shell.legal.external': { purpose: 'The original document on its own website.', effect: 'Opens in a new tab, so this page stays open.' },
  'shell.credit.model': { purpose: 'The 3D model is open data used under its licence.', effect: 'Opens the credits with its source and changes.' },
} as const satisfies Record<string, Tip>;
