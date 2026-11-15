/** A control's description: what it is for (purpose) and what happens (effect). */
export interface Tip {
  purpose: string;
  effect: string;
  /** Why the control is unavailable right now. Shown when it is disabled. */
  disabled?: string;
}

/** Marks a control that deliberately has no tip. Needs an adjacent comment saying why (check-tips enforces it). */
export const NO_TIP = '__no_tip__' as const;
