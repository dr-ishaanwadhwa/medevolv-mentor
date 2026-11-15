/**
 * Central tip registry. One file per feature (each owned by that feature's workstream),
 * merged here into a single `TipId` type. Add new files to the spread below.
 *
 * Copy rules (checked in review):
 * 1. Never repeat the visible label ("Send: Sends" is not allowed).
 * 2. State purpose AND effect. Obvious controls may use one combined sentence.
 * 3. Effect-first wording for non-obvious controls.
 * 4. Use data where it helps (citation pointer, chapter title).
 * 5. Plain words, about 20 words at most, nothing a first-year would not know.
 */
import type { Tip } from './types';
import { SHELL_TIPS } from './shell';
import { WHY_TIPS } from './why';
import { EXPLORE_TIPS } from './explore';
import { STORY_TIPS } from './story';

export type { Tip } from './types';
export { NO_TIP } from './types';

export const TIPS = {
  ...SHELL_TIPS,
  ...WHY_TIPS,
  ...EXPLORE_TIPS,
  ...STORY_TIPS,
} as const satisfies Record<string, Tip>;

export type TipId = keyof typeof TIPS;

/** What the `tip` prop accepts: a registry id or a plain object (so server components can pass one). */
export type TipProp = TipId | Tip | typeof import('./types').NO_TIP;

export function resolveTip(tip: TipProp | undefined): Tip | null {
  if (!tip || tip === '__no_tip__') return null;
  if (typeof tip === 'string') return (TIPS as Record<string, Tip>)[tip] ?? null;
  return tip;
}

/** The text a screen reader announces (and the bubble shows) for a tip. */
export function tipText(tip: Tip, disabled = false): string {
  if (disabled && tip.disabled) return tip.disabled;
  return `${tip.purpose} ${tip.effect}`;
}
