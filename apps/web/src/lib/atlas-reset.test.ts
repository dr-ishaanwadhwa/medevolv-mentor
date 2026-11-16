import { describe, expect, it } from 'vitest';
import * as T from 'three';
import { hasSomethingToUndo, resetIntent, withSelection, type ViewState } from './atlas-reset';
import { computeGoalPose } from './atlas-camera';

const goal = { target: new T.Vector3(1, 2, 3), position: new T.Vector3(4, 5, 6) };
const prev: ViewState = { selection: ['FMA62045'], isolate: true, goal, hidden: ['FJ1', 'FJ2'], explode: 0.3 };
const view = { width: 1000, height: 800, aspect: 1.25, fov: 34 };
const box = (x: number, y: number, z: number, s: number) =>
  new T.Box3(new T.Vector3(x - s, y - s, z - s), new T.Vector3(x + s, y + s, z + s));
const boxes = [box(0, 0.2, 0, 0.2), box(0.5, 1.0, 0.1, 0.3), box(-0.4, 1.6, 0, 0.15)];

describe('resetIntent', () => {
  it('clears selection and isolate and frames the whole body', () => {
    const i = resetIntent(prev);
    expect(i.selection).toEqual([]);
    expect(i.isolate).toBe(false);
    expect(i.frameParts).toEqual([]);
  });
  it('is idempotent: two resets in a row give the same intent (RV-5)', () => {
    const first = resetIntent(prev);
    const second = resetIntent({ selection: first.selection, isolate: first.isolate, goal, hidden: first.hidden, explode: first.explode });
    expect(second.selection).toEqual(first.selection);
    expect(second.isolate).toBe(first.isolate);
    expect(second.frameParts).toEqual(first.frameParts);
  });
  it('keeps the previous selection, isolate and goal for Undo, as copies', () => {
    const i = resetIntent(prev);
    expect(i.undo).toEqual(prev);
    expect(i.undo.selection).not.toBe(prev.selection);
  });
});

describe('Reset view and hidden structures / explode', () => {
  it('clears the hidden set and the explode amount, and Undo keeps copies of both', () => {
    const i = resetIntent(prev);
    expect(i.hidden).toEqual([]);
    expect(i.explode).toBe(0);
    expect(i.undo.hidden).toEqual(['FJ1', 'FJ2']);
    expect(i.undo.hidden).not.toBe(prev.hidden);
    expect(i.undo.explode).toBe(0.3);
  });
  it('is undoable when only something is hidden or exploded', () => {
    const base = { selection: [], isolate: false, goal: null };
    expect(hasSomethingToUndo({ ...base, hidden: ['FJ1'], explode: 0 }, false)).toBe(true);
    expect(hasSomethingToUndo({ ...base, hidden: [], explode: 0.3 }, false)).toBe(true);
  });
  it('store: Reset view empties the hidden set and the explode amount; Undo can put them back', async () => {
    const { useAtlasStore } = await import('./atlas-store');
    const st = useAtlasStore.getState();
    st.hideParts(['FJ1', 'FJ2']);
    st.setExplode(0.3);
    const intent = resetIntent({ selection: [], isolate: false, goal: null, hidden: useAtlasStore.getState().hiddenParts, explode: useAtlasStore.getState().explode });
    useAtlasStore.getState().reset();
    expect(useAtlasStore.getState().hiddenParts).toEqual([]);
    expect(useAtlasStore.getState().explode).toBe(0);
    useAtlasStore.getState().setHiddenParts(intent.undo.hidden);
    useAtlasStore.getState().setExplode(intent.undo.explode);
    expect(useAtlasStore.getState().hiddenParts).toEqual(['FJ1', 'FJ2']);
    expect(useAtlasStore.getState().explode).toBe(0.3);
    useAtlasStore.getState().reset();
  });
});

describe('hasSomethingToUndo', () => {
  it('is false for a pristine view and true otherwise', () => {
    expect(hasSomethingToUndo({ selection: [], isolate: false, goal: null, hidden: [], explode: 0 }, false)).toBe(false);
    expect(hasSomethingToUndo({ selection: [], isolate: false, goal: null, hidden: [], explode: 0 }, true)).toBe(true);
    expect(hasSomethingToUndo({ selection: ['A'], isolate: false, goal: null, hidden: [], explode: 0 }, false)).toBe(true);
    expect(hasSomethingToUndo({ selection: [], isolate: true, goal: null, hidden: [], explode: 0 }, false)).toBe(true);
  });
});

describe('withSelection (RV-1)', () => {
  it('removes select and keeps other params', () => {
    expect(withSelection('?select=FMA1&sex=female', [])).toBe('?sex=female');
    expect(withSelection('?select=FMA1', [])).toBe('');
  });
  it('sets select and keeps other params', () => {
    expect(withSelection('?sex=female', ['FMA1', 'FMA2'])).toBe('?select=FMA1,FMA2&sex=female');
    expect(withSelection('', ['HRA:VH_F_UTERUS'])).toBe('?select=HRA%3AVH_F_UTERUS');
  });
});

describe('computeGoalPose', () => {
  it('whole-body pose equals the pose of the union of all visible boxes, within 1e-6', () => {
    const whole = computeGoalPose(boxes, true, undefined, view)!;
    const union = new T.Box3();
    boxes.forEach((b) => union.union(b));
    const again = computeGoalPose([union], true, undefined, view)!;
    expect(whole.target.distanceTo(again.target)).toBeLessThan(1e-6);
    expect(whole.position.distanceTo(again.position)).toBeLessThan(1e-6);
  });
  it('differs from the pose for one selected box', () => {
    const whole = computeGoalPose(boxes, true, undefined, view)!;
    const one = computeGoalPose([boxes[1]], false, undefined, view)!;
    expect(whole.target.distanceTo(one.target)).toBeGreaterThan(0.1);
  });
  it('shifts framing for a panel inset and returns null for nothing to frame', () => {
    const a = computeGoalPose(boxes, true, undefined, view)!;
    const b = computeGoalPose(boxes, true, { right: 436 }, view)!;
    expect(b.dist).toBeGreaterThan(a.dist - 1e-9);
    expect(computeGoalPose([], true, undefined, view)).toBeNull();
  });
});
