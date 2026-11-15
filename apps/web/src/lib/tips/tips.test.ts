import { describe, expect, it } from 'vitest';
import { TIPS, resolveTip, tipText } from './index';

describe('tips registry', () => {
  const entries = Object.entries(TIPS) as [string, { purpose: string; effect: string; disabled?: string }][];

  it('has copy for every id: purpose and effect, plain and short', () => {
    for (const [id, t] of entries) {
      expect(t.purpose.trim().length, id).toBeGreaterThan(0);
      expect(t.effect.trim().length, id).toBeGreaterThan(0);
      const words = `${t.purpose} ${t.effect}`.split(/\s+/).length;
      expect(words, `${id} is ${words} words`).toBeLessThanOrEqual(26);
    }
  });

  it('ids are namespaced by feature', () => {
    for (const [id] of entries) expect(id, id).toMatch(/^(shell|why|explore|story|atlas|answer|landing)\./);
  });

  it('resolves ids and plain objects, and ignores the NO_TIP marker', () => {
    expect(resolveTip('why.submit')?.disabled).toBeTruthy();
    const custom = { purpose: 'p', effect: 'e' };
    expect(resolveTip(custom)).toBe(custom);
    expect(resolveTip('__no_tip__')).toBeNull();
    expect(resolveTip(undefined)).toBeNull();
  });

  it('shows the disabled reason only when disabled and one exists', () => {
    const t = TIPS['why.submit'];
    expect(tipText(t, true)).toBe(t.disabled);
    expect(tipText(t, false)).toBe(`${t.purpose} ${t.effect}`);
    expect(tipText(TIPS['why.edit'], true)).toBe(`${TIPS['why.edit'].purpose} ${TIPS['why.edit'].effect}`);
  });
});
