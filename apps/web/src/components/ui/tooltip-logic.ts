/**
 * Framework-free tooltip behaviour (timers, single-open store, long-press, placement).
 * Kept apart from React so it runs under the node unit runner.
 */

export const HOVER_DELAY_MS = 500;
export const LEAVE_GRACE_MS = 100;
export const LONG_PRESS_MS = 500;
export const LONG_PRESS_MOVE_PX = 10;

/** Module-level store: only one tooltip is open at a time. */
type Listener = () => void;
let openId: string | null = null;
const listeners = new Set<Listener>();
const emit = () => listeners.forEach((l) => l());

export const tipStore = {
  get: () => openId,
  subscribe(l: Listener) {
    listeners.add(l);
    return () => {
      listeners.delete(l);
    };
  },
  open(id: string) {
    if (openId === id) return;
    openId = id;
    emit();
  },
  close(id?: string) {
    if (openId === null || (id !== undefined && openId !== id)) return;
    openId = null;
    emit();
  },
};

export interface TriggerController {
  hoverEnter(): void;
  hoverLeave(): void;
  /** `visible` is true for keyboard focus (:focus-visible), false for mouse or touch focus. */
  focus(visible: boolean): void;
  blur(): void;
  escape(): void;
  bubbleEnter(): void;
  bubbleLeave(): void;
  touchDown(x: number, y: number): void;
  touchMove(x: number, y: number): void;
  /** Returns true when the tip was shown by this press, so the click that follows should be swallowed. */
  touchUp(): boolean;
  touchCancel(): void;
  /** True once if a long-press just showed the tip (consumes the flag). */
  consumeSuppressedClick(): boolean;
  dispose(): void;
}

/** One controller per trigger element. `id` identifies the tooltip in the single-open store. */
export function createTriggerController(id: string, opts: { longPress?: boolean } = {}): TriggerController {
  let hoverTimer: ReturnType<typeof setTimeout> | undefined;
  let leaveTimer: ReturnType<typeof setTimeout> | undefined;
  let pressTimer: ReturnType<typeof setTimeout> | undefined;
  let clearSuppress: ReturnType<typeof setTimeout> | undefined;
  let start: { x: number; y: number } | null = null;
  let shownByPress = false;
  let suppress = false;

  const stopHover = () => {
    clearTimeout(hoverTimer);
    hoverTimer = undefined;
  };
  const stopLeave = () => {
    clearTimeout(leaveTimer);
    leaveTimer = undefined;
  };
  const stopPress = () => {
    clearTimeout(pressTimer);
    pressTimer = undefined;
    start = null;
  };
  const scheduleClose = () => {
    stopHover();
    stopLeave();
    leaveTimer = setTimeout(() => tipStore.close(id), LEAVE_GRACE_MS);
  };

  return {
    hoverEnter() {
      stopLeave();
      if (tipStore.get() === id) return;
      stopHover();
      hoverTimer = setTimeout(() => tipStore.open(id), HOVER_DELAY_MS);
    },
    hoverLeave: scheduleClose,
    focus(visible) {
      if (!visible) return;
      stopHover();
      stopLeave();
      tipStore.open(id);
    },
    blur() {
      stopHover();
      stopLeave();
      tipStore.close(id);
    },
    escape() {
      stopHover();
      stopLeave();
      tipStore.close(id);
    },
    bubbleEnter: stopLeave,
    bubbleLeave: scheduleClose,
    touchDown(x, y) {
      if (!opts.longPress) return;
      stopPress();
      clearTimeout(clearSuppress);
      suppress = false;
      shownByPress = false;
      start = { x, y };
      pressTimer = setTimeout(() => {
        // Only fires while the finger is still down and has not moved past the tolerance.
        shownByPress = true;
        pressTimer = undefined;
        tipStore.open(id);
      }, LONG_PRESS_MS);
    },
    touchMove(x, y) {
      if (!start || pressTimer === undefined) return;
      if (Math.hypot(x - start.x, y - start.y) > LONG_PRESS_MOVE_PX) stopPress();
    },
    touchUp() {
      stopPress();
      if (!shownByPress) return false;
      shownByPress = false;
      suppress = true;
      // The synthetic click, if any, arrives immediately; do not suppress a later, unrelated one.
      clearSuppress = setTimeout(() => {
        suppress = false;
      }, 400);
      return true;
    },
    touchCancel() {
      stopPress();
      shownByPress = false;
    },
    consumeSuppressedClick() {
      if (!suppress) return false;
      suppress = false;
      clearTimeout(clearSuppress);
      return true;
    },
    dispose() {
      stopHover();
      stopLeave();
      stopPress();
      clearTimeout(clearSuppress);
      tipStore.close(id);
    },
  };
}

export interface Box {
  top: number;
  left: number;
  width: number;
  height: number;
}

/**
 * Place a bubble above its trigger, flipping below when there is no room above,
 * clamped horizontally into the viewport. Never overlaps the trigger.
 */
export function computePosition(
  trigger: Box,
  bubble: { width: number; height: number },
  viewport: { width: number; height: number },
  gap = 8,
  margin = 8,
): { top: number; left: number; placement: 'above' | 'below' } {
  const above = trigger.top - gap - bubble.height;
  const below = trigger.top + trigger.height + gap;
  const fitsBelow = below + bubble.height <= viewport.height - margin;
  const placement: 'above' | 'below' = above >= margin || !fitsBelow ? 'above' : 'below';
  const rawTop = placement === 'above' ? above : below;
  const top = Math.max(margin, rawTop);
  const centred = trigger.left + trigger.width / 2 - bubble.width / 2;
  const left = Math.min(Math.max(margin, centred), Math.max(margin, viewport.width - bubble.width - margin));
  return { top, left, placement };
}
