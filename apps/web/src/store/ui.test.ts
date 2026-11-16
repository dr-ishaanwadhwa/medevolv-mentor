import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useUi } from './ui';

beforeEach(() => {
  vi.useFakeTimers();
  useUi.setState({ toasts: [] });
});
afterEach(() => vi.useRealTimers());

describe('toast', () => {
  it('still accepts the old (text, ms) form', () => {
    useUi.getState().toast('Saved', 1000);
    expect(useUi.getState().toasts).toHaveLength(1);
    vi.advanceTimersByTime(1000);
    expect(useUi.getState().toasts).toHaveLength(0);
  });

  it('keeps an action toast longer by default and carries the action', () => {
    const onClick = vi.fn();
    useUi.getState().toast('View reset', { action: { label: 'Undo', onClick } });
    const [t] = useUi.getState().toasts;
    expect(t.action?.label).toBe('Undo');
    vi.advanceTimersByTime(2700);
    expect(useUi.getState().toasts).toHaveLength(1);
    vi.advanceTimersByTime(3400);
    expect(useUi.getState().toasts).toHaveLength(0);
    t.action?.onClick();
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('pauses the dismiss timer while hovered or focused and resumes with the time left', () => {
    const id = useUi.getState().toast('View reset', { ms: 5000, action: { label: 'Undo', onClick: () => {} } });
    vi.advanceTimersByTime(4000);
    useUi.getState().pause(id);
    vi.advanceTimersByTime(60_000);
    expect(useUi.getState().toasts).toHaveLength(1);
    useUi.getState().resume(id);
    vi.advanceTimersByTime(1400);
    expect(useUi.getState().toasts).toHaveLength(1); // at least 1.5 s after leaving
    vi.advanceTimersByTime(200);
    expect(useUi.getState().toasts).toHaveLength(0);
  });

  it('carries a specific tip for the action', () => {
    useUi.getState().toast('View reset', { action: { label: 'Undo', onClick: () => {}, tip: { purpose: 'p', effect: 'e' } } });
    expect(useUi.getState().toasts[0].action?.tip).toEqual({ purpose: 'p', effect: 'e' });
  });

  it('dismiss removes one toast', () => {
    const id = useUi.getState().toast('x');
    useUi.getState().dismiss(id);
    expect(useUi.getState().toasts).toHaveLength(0);
  });
});
