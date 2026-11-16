import { describe, expect, it } from 'vitest';
import { anyHidden, hideParts, revealParts } from './atlas-hidden';
import { useAtlasStore } from './atlas-store';

describe('hidden set', () => {
  it('adds parts once, keeping the order they were hidden', () => {
    expect(hideParts(['A'], ['B', 'A', 'C', 'B'])).toEqual(['A', 'B', 'C']);
  });
  it('does not mutate its input', () => {
    const h = ['A'];
    hideParts(h, ['B']);
    revealParts(h, ['A']);
    expect(h).toEqual(['A']);
  });
  it('reveals only the named parts', () => {
    expect(revealParts(['A', 'B', 'C'], ['B', 'Z'])).toEqual(['A', 'C']);
  });
  it('anyHidden tells whether a selection touches the hidden set', () => {
    expect(anyHidden([], ['A'])).toBe(false);
    expect(anyHidden(['A', 'B'], ['C', 'B'])).toBe(true);
    expect(anyHidden(['A'], ['C'])).toBe(false);
  });
});

describe('hidden set in the store', () => {
  it('survives selection-style updates and only clears on restore, reset or reveal', () => {
    const s = () => useAtlasStore.getState();
    s().setHiddenParts([]);
    s().hideParts(['FJ1']);
    s().hideParts(['FJ2']);
    s().setIsolate(true); // unrelated state changes leave it alone
    s().setIsolate(false);
    expect(s().hiddenParts).toEqual(['FJ1', 'FJ2']);
    s().revealParts(['FJ1']);
    expect(s().hiddenParts).toEqual(['FJ2']);
    const same = s().hiddenParts;
    s().revealParts(['NOPE']); // nothing to reveal: no new array, so subscribers do not re-render
    expect(s().hiddenParts).toBe(same);
    s().setHiddenParts([]);
    expect(s().hiddenParts).toEqual([]);
  });
});
