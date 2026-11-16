import type { Tip } from './types';

/** Answer card, flowchart, related topics and suggested videos. Owner: WS-X. */
export const ANSWER_TIPS = {
  'answer.share': { purpose: 'Makes a public link to this answer.', effect: 'Copies the link; textbook excerpts are left out.' },
  'answer.feedback': { purpose: 'Tells us something is wrong with this answer.', effect: 'Opens a short form below.' },
  'answer.feedback.kind': { purpose: 'Picks what went wrong.', effect: 'Sent with your report.' },
  'answer.feedback.cancel': { purpose: 'Closes the report form.', effect: 'Nothing is sent.' },
  'answer.feedback.send': {
    purpose: 'Sends your report to the team.',
    effect: 'Stores the question, the problem type and your note.',
    disabled: 'Pick what went wrong first.',
  },
  'answer.flowchart': {
    purpose: 'Turns this answer into a revision flowchart.',
    effect: 'Every box and arrow links to its source. Takes a few seconds.',
    disabled: 'Working on it',
  },
  'answer.flowchart.retry': { purpose: 'Tries drawing the flowchart again.', effect: 'Sends one new request.' },
  'answer.flowchart.askInstead': { purpose: 'Asks a question that suits a flowchart better.', effect: 'Adds it as a new question below.' },
  'answer.diagram.save': {
    purpose: 'Saves the flowchart as a picture.',
    effect: 'White background, with the sources and the study-aid line. Opens the share sheet where possible.',
  },
  'answer.diagram.fullscreen': { purpose: 'Shows the flowchart on the whole screen.', effect: 'Zoom and scroll there; Escape closes it.' },
  'answer.diagram.more': { purpose: 'More flowchart actions.', effect: 'Opens a menu: save as SVG, report a problem.' },
  'answer.diagram.svg': { purpose: 'Saves the flowchart as an SVG file.', effect: 'Sharp at any size, with the sources.' },
  'answer.diagram.report': { purpose: 'Tells us a box or arrow is wrong.', effect: 'Sends a report about this flowchart.' },
  'answer.diagram.close': { purpose: 'Leaves full screen.', effect: 'Returns to the answer.' },
  'answer.diagram.zoomIn': { purpose: 'Makes the flowchart bigger.', effect: 'Scroll to move around.' },
  'answer.diagram.zoomOut': { purpose: 'Makes the flowchart smaller.', effect: 'Shows more of it at once.' },
  'answer.diagram.branch': { purpose: 'Shows or hides the boxes under this one.', effect: 'The tree grows or shrinks in place.' },
  'answer.diagram.sources': { purpose: 'Lists the textbook facts this flowchart uses.', effect: 'Opens book, chapter and page for each.' },
  'answer.related': { purpose: 'A topic linked to this one in the textbooks.', effect: 'Asks it as a new question below.' },
  'answer.videos.watch': { purpose: 'Opens this video on YouTube in a new tab.', effect: 'Not checked by MedEvolv.' },
  'answer.videos.menu': { purpose: 'Options for this video.', effect: 'Opens a menu with Report this video.' },
  'answer.videos.report': { purpose: 'Tells us this video is unsuitable.', effect: 'The team can block it for everyone.' },
  'answer.videos.search': { purpose: 'Searches YouTube for this topic.', effect: 'Opens YouTube in a new tab.' },
  'answer.videos.youtube': { purpose: 'The source of these suggestions.', effect: 'Opens YouTube in a new tab.' },
  'answer.videos.terms': { purpose: "YouTube's Terms of Service.", effect: 'Opens them in a new tab.' },
  'answer.legal.terms': { purpose: 'Our terms, including the video suggestions.', effect: 'Opens the Terms page.' },
  'answer.legal.privacy': { purpose: 'What we store and what YouTube receives.', effect: 'Opens the Privacy page.' },
  'answer.shared.ask': { purpose: 'Opens Mentor to ask a question of your own.', effect: 'Answers cite book, chapter and page.' },
} as const satisfies Record<string, Tip>;

export type AnswerTipId = keyof typeof ANSWER_TIPS;
