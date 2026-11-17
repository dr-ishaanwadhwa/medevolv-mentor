/**
 * Flowchart copy map (PRD 4.1 UX table, D-17). Every `reason` the API documents and every error status maps to
 * exactly one row here; `diagram.test.ts` imports this table. No `@/` imports: the unit runner loads it directly.
 */

export const STUDY_AID_LINE = 'Study aid summarised from textbooks. Not for decisions about a real patient.';

export const BADGE = {
  ontology: 'From certified facts',
  answer: "Drawn from this answer's citations",
} as const;

export const CHIP_LABEL = 'Flowchart';

/** Loading text; `k` is the highest passage marker in the answer (0 when it cites only graph facts). */
export function loadingCopy(k: number): string {
  return k > 1 ? `Drawing a flowchart from citations [1]-[${k}]...` : 'Drawing a flowchart from the citations...';
}

export interface DiagramUx {
  /** Text in the muted card; null = no card at all. */
  copy: string | null;
  /** A Retry button inside the card. */
  retry: boolean;
  /** Offer a tap-to-ask chip (only for validator declines, and only when a subject is known). */
  askChip: boolean;
  /** Hide the Flowchart chip for this answer. */
  hideChip: boolean;
  /** 'page': chip disabled for the rest of the page load; 'minute': disabled for 60 s; 'none': enabled. */
  chipLock: 'none' | 'minute' | 'page';
  /** Disabled-tip text while locked. */
  lockTip?: string;
}

export const COPY = {
  notEnough:
    "This answer doesn't have enough cited steps for a flowchart. Try asking for a classification, pathway or mechanism.",
  failed: "Couldn't draw it right now.",
  /** verifier_unavailable: a flowchart was drawn but could not be checked box by box against its sources, so none is
   *  shown (the chip's tip promises every box and arrow links to its source). Not deterministic: Retry. */
  unverified: "Couldn't check this flowchart against its sources right now.",
  budget: 'Flowcharts are paused for today.',
  rateLimited: 'Too many requests, try again in a minute.',
  working: 'Working on it',
  paused: 'Paused for today',
  wait: 'Try again in a minute',
} as const;

/** Reasons that come from the deterministic validator: the same answer always gives the same result, so no Retry. */
export const VALIDATOR_REASONS = ['too_few_supported_nodes'] as const;

const VALIDATOR: DiagramUx = { copy: COPY.notEnough, retry: false, askChip: true, hideChip: false, chipLock: 'none' };
const FAILED_RETRY: DiagramUx = { copy: COPY.failed, retry: true, askChip: false, hideChip: false, chipLock: 'none' };
const GONE: DiagramUx = { copy: null, retry: false, askChip: false, hideChip: true, chipLock: 'none' };

export type DiagramOutcome =
  | { kind: 'declined'; reason: string }
  | { kind: 'http'; status: number }
  | { kind: 'abort' }
  | { kind: 'network' };

export function diagramUx(o: DiagramOutcome): DiagramUx {
  if (o.kind === 'declined') {
    if ((VALIDATOR_REASONS as readonly string[]).includes(o.reason)) return VALIDATOR;
    if (o.reason === 'generator_error') return FAILED_RETRY;
    if (o.reason === 'verifier_unavailable')
      return { copy: COPY.unverified, retry: true, askChip: false, hideChip: false, chipLock: 'none' };
    if (o.reason === 'budget')
      return { copy: COPY.budget, retry: false, askChip: false, hideChip: false, chipLock: 'page', lockTip: COPY.paused };
    // Patient-scoped questions never offer the chip; if the server still says so, remove everything quietly.
    if (o.reason === 'patient_scoped') return GONE;
    // Unknown future reason: the generator_error copy without Retry.
    return { copy: COPY.failed, retry: false, askChip: false, hideChip: false, chipLock: 'none' };
  }
  if (o.kind === 'http') {
    if (o.status === 403 || o.status === 503) return GONE;
    if (o.status === 429)
      return { copy: COPY.rateLimited, retry: false, askChip: false, hideChip: false, chipLock: 'minute', lockTip: COPY.wait };
    return FAILED_RETRY;
  }
  return FAILED_RETRY; // client abort at 35 s, or a network error
}

/** Tap-to-ask suggestion for a validator decline, when the answer's topic is known. */
export function askInstead(subject: string | null | undefined): string | null {
  const s = (subject ?? '').trim();
  return s ? `Classify ${s}` : null;
}
