import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  HOVER_DELAY_MS,
  LEAVE_GRACE_MS,
  LONG_PRESS_MS,
  computePosition,
  createTriggerController,
  tipStore,
} from './tooltip-logic';

beforeEach(() => {
  vi.useFakeTimers();
  tipStore.close();
});
afterEach(() => {
  vi.useRealTimers();
});

describe('hover', () => {
  it('opens after 500 ms, not before', () => {
    const c = createTriggerController('a');
    c.hoverEnter();
    vi.advanceTimersByTime(HOVER_DELAY_MS - 1);
    expect(tipStore.get()).toBeNull();
    vi.advanceTimersByTime(1);
    expect(tipStore.get()).toBe('a');
  });

  it('does not open if the pointer leaves first', () => {
    const c = createTriggerController('a');
    c.hoverEnter();
    vi.advanceTimersByTime(200);
    c.hoverLeave();
    vi.advanceTimersByTime(1000);
    expect(tipStore.get()).toBeNull();
  });

  it('stays open while the pointer moves onto the bubble (100 ms grace)', () => {
    const c = createTriggerController('a');
    c.hoverEnter();
    vi.advanceTimersByTime(HOVER_DELAY_MS);
    c.hoverLeave();
    vi.advanceTimersByTime(LEAVE_GRACE_MS - 10);
    c.bubbleEnter();
    vi.advanceTimersByTime(1000);
    expect(tipStore.get()).toBe('a');
    c.bubbleLeave();
    vi.advanceTimersByTime(LEAVE_GRACE_MS);
    expect(tipStore.get()).toBeNull();
  });

  it('closes after the grace period when nothing hovers it', () => {
    const c = createTriggerController('a');
    c.hoverEnter();
    vi.advanceTimersByTime(HOVER_DELAY_MS);
    c.hoverLeave();
    vi.advanceTimersByTime(LEAVE_GRACE_MS);
    expect(tipStore.get()).toBeNull();
  });
});

describe('keyboard', () => {
  it('opens at once on keyboard focus, ignores mouse focus', () => {
    const c = createTriggerController('a');
    c.focus(false);
    expect(tipStore.get()).toBeNull();
    c.focus(true);
    expect(tipStore.get()).toBe('a');
  });

  it('closes on blur and on Escape', () => {
    const c = createTriggerController('a');
    c.focus(true);
    c.blur();
    expect(tipStore.get()).toBeNull();
    c.focus(true);
    c.escape();
    expect(tipStore.get()).toBeNull();
  });
});

describe('single open tooltip', () => {
  it('opening one closes the other', () => {
    const a = createTriggerController('a');
    const b = createTriggerController('b');
    a.focus(true);
    b.focus(true);
    expect(tipStore.get()).toBe('b');
    a.blur(); // must not close b
    expect(tipStore.get()).toBe('b');
  });
});

describe('touch long-press (icon-only buttons)', () => {
  it('shows the tip after 500 ms and swallows the click that follows that press', () => {
    const c = createTriggerController('a', { longPress: true });
    c.touchDown(10, 10);
    vi.advanceTimersByTime(LONG_PRESS_MS);
    expect(tipStore.get()).toBe('a');
    expect(c.touchUp()).toBe(true);
    expect(c.consumeSuppressedClick()).toBe(true);
    expect(c.consumeSuppressedClick()).toBe(false); // only once
  });

  it('a quick tap shows nothing and never suppresses the click', () => {
    const c = createTriggerController('a', { longPress: true });
    c.touchDown(10, 10);
    vi.advanceTimersByTime(200);
    expect(c.touchUp()).toBe(false);
    vi.advanceTimersByTime(1000);
    expect(tipStore.get()).toBeNull();
    expect(c.consumeSuppressedClick()).toBe(false);
  });

  it('a synthetic click with no preceding press (screen reader double-tap) is never suppressed', () => {
    const c = createTriggerController('a', { longPress: true });
    expect(c.consumeSuppressedClick()).toBe(false);
  });

  it('moving more than 10 px cancels the long-press', () => {
    const c = createTriggerController('a', { longPress: true });
    c.touchDown(0, 0);
    c.touchMove(11, 0);
    vi.advanceTimersByTime(LONG_PRESS_MS + 100);
    expect(tipStore.get()).toBeNull();
  });

  it('moving under 10 px keeps it', () => {
    const c = createTriggerController('a', { longPress: true });
    c.touchDown(0, 0);
    c.touchMove(6, 6);
    vi.advanceTimersByTime(LONG_PRESS_MS);
    expect(tipStore.get()).toBe('a');
  });

  it('is off unless the control opted in (links and text buttons)', () => {
    const c = createTriggerController('a');
    c.touchDown(0, 0);
    vi.advanceTimersByTime(LONG_PRESS_MS * 2);
    expect(tipStore.get()).toBeNull();
    expect(c.touchUp()).toBe(false);
  });

  it('a stale suppress flag expires so a later click still works', () => {
    const c = createTriggerController('a', { longPress: true });
    c.touchDown(0, 0);
    vi.advanceTimersByTime(LONG_PRESS_MS);
    c.touchUp();
    vi.advanceTimersByTime(1000);
    expect(c.consumeSuppressedClick()).toBe(false);
  });
});

describe('computePosition', () => {
  const vp = { width: 400, height: 800 };
  const bubble = { width: 200, height: 40 };

  it('goes above the trigger, centred, and does not overlap it', () => {
    const p = computePosition({ top: 300, left: 100, width: 40, height: 40 }, bubble, vp);
    expect(p.placement).toBe('above');
    expect(p.top + bubble.height).toBeLessThanOrEqual(300);
    expect(p.left).toBe(100 + 20 - 100);
  });

  it('flips below near the top edge', () => {
    const p = computePosition({ top: 10, left: 100, width: 40, height: 40 }, bubble, vp);
    expect(p.placement).toBe('below');
    expect(p.top).toBeGreaterThanOrEqual(50);
  });

  it('is clamped into the viewport horizontally', () => {
    const left = computePosition({ top: 300, left: 0, width: 20, height: 20 }, bubble, vp);
    const right = computePosition({ top: 300, left: 390, width: 10, height: 20 }, bubble, vp);
    expect(left.left).toBeGreaterThanOrEqual(8);
    expect(right.left + bubble.width).toBeLessThanOrEqual(vp.width - 8);
  });
});
