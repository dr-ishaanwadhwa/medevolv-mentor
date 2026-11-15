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

  it('dismiss removes one toast', () => {
    const id = useUi.getState().toast('x');
    useUi.getState().dismiss(id);
    expect(useUi.getState().toasts).toHaveLength(0);
  });
});
