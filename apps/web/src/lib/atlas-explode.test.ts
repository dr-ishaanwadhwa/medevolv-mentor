import { describe, expect, it } from 'vitest';
import type { SystemId } from './anatomy';
import {
  EXPLODE_FAMILY_BY_SYSTEM,
  SYSTEM_SEPARATION_END,
  createExplodeLayout,
  explodeFamilyCount,
  explodeOffset,
  explodePlaybackAt,
  explodeProgress,
  explodeStageText,
  nextExplodeStop,
  planExplodePlayback,
} from './atlas-explode';

const part = (id: string, system: SystemId, x: number, y: number, w = 0.1, h = 0.2) => ({
  id,
  system,
  bounds: [[x - w / 2, y - h / 2, -0.05], [x + w / 2, y + h / 2, 0.05]] as [number[], number[]],
});
const body = [
  part('bone1', 'skeletal', -0.2, 1.4),
  part('bone2', 'skeletal', 0.2, 0.6),
  part('muscle1', 'muscular', 0, 1.0),
  part('heart', 'cardiac', 0, 1.2, 0.12, 0.12),
  part('nerve', 'nervous', 0.3, 1.0),
];

describe('families', () => {
  it('every system maps to a family (both models)', () => {
    for (const f of Object.values(EXPLODE_FAMILY_BY_SYSTEM)) expect(f).toBeTruthy();
    expect(explodeFamilyCount(body)).toBe(4);
    expect(explodeFamilyCount([part('s', 'integumentary', 0, 0)])).toBe(0);
  });
});

describe('explodeProgress', () => {
  it('moves families first, then pieces, with no overlap', () => {
    expect(explodeProgress(0, 4)).toEqual({ family: 0, piece: 0 });
    const mid = explodeProgress(SYSTEM_SEPARATION_END, 4);
    expect(mid.family).toBeCloseTo(1, 10);
    expect(mid.piece).toBeCloseTo(0, 10);
    expect(explodeProgress(1, 4)).toEqual({ family: 1, piece: 1 });
  });
  it('is monotone and smooth (eased, no jump)', () => {
    let last = -1;
    for (let t = 0; t <= 1.0001; t += 0.01) {
      const p = explodeProgress(t, 4);
      const total = p.family + p.piece;
      expect(total).toBeGreaterThanOrEqual(last - 1e-12);
      last = total;
    }
    expect(explodeProgress(0.01, 4).family).toBeLessThan(0.01);
  });
  it('a single family skips stage 1 and clamps bad input', () => {
    expect(explodeProgress(0.3, 1).family).toBe(0);
    expect(explodeProgress(0.5, 1).piece).toBeCloseTo(0.5, 10);
    expect(explodeProgress(Number.NaN, 4)).toEqual({ family: 0, piece: 0 });
    expect(explodeProgress(5, 4).piece).toBe(1);
  });
});

describe('createExplodeLayout / explodeOffset', () => {
  const layout = createExplodeLayout(body);
  it('has a target for every part and one lane per family', () => {
    expect(layout.targets.size).toBe(body.length);
    expect(layout.familyCount).toBe(4);
  });
  it('is the identity when assembled', () => {
    for (const t of layout.targets.values()) expect(explodeOffset(t, 0, layout.familyCount)).toEqual([0, 0, 0]);
  });
  it('stage 1 moves only along x and keeps a family together', () => {
    const [a, b] = ['bone1', 'bone2'].map((id) => explodeOffset(layout.targets.get(id)!, SYSTEM_SEPARATION_END, layout.familyCount));
    expect(a).toEqual(b); // both skeleton parts slide by the same amount
    expect(a[1]).toBeCloseTo(0, 10);
    expect(a[2]).toBeCloseTo(0, 10);
    const lanes = new Set(['bone1', 'muscle1', 'heart', 'nerve'].map((id) => explodeOffset(layout.targets.get(id)!, SYSTEM_SEPARATION_END, 4)[0].toFixed(4)));
    expect(lanes.size).toBe(4); // the four families end up in four different lanes
  });
  it('stage 2 lays every piece in its own cell: no two pieces overlap', () => {
    const boxes = body.map((p) => {
      const o = explodeOffset(layout.targets.get(p.id)!, 1, layout.familyCount);
      return { min: p.bounds[0].map((n, a) => n + o[a]), max: p.bounds[1].map((n, a) => n + o[a]) };
    });
    for (let i = 0; i < boxes.length; i++)
      for (let j = i + 1; j < boxes.length; j++) {
        const overlap = boxes[i].min[0] < boxes[j].max[0] && boxes[j].min[0] < boxes[i].max[0] && boxes[i].min[1] < boxes[j].max[1] && boxes[j].min[1] < boxes[i].max[1];
        expect(overlap, `${body[i].id} vs ${body[j].id}`).toBe(false);
      }
  });
  it('is stable: the same parts give the same offsets whatever order they come in', () => {
    const again = createExplodeLayout([...body].reverse());
    for (const p of body) expect(explodeOffset(again.targets.get(p.id)!, 0.7, 4)).toEqual(explodeOffset(layout.targets.get(p.id)!, 0.7, 4));
  });
  it('one part, or one family, never separates sideways', () => {
    const solo = createExplodeLayout([body[0]]);
    expect(explodeOffset(solo.targets.get('bone1')!, 1, 1)).toEqual([0, 0, 0]);
    const one = createExplodeLayout([body[0], body[1]]);
    expect(one.familyCount).toBe(1);
    expect(one.targets.get('bone1')!.familyTranslation).toEqual([0, 0, 0]);
  });
});

describe('stage text and stops', () => {
  it('names each stage', () => {
    expect(explodeStageText(0, 4)).toBe('Assembled');
    expect(explodeStageText(SYSTEM_SEPARATION_END, 4)).toBe('Systems apart');
    expect(explodeStageText(0.1, 4)).toBe('Separating systems');
    expect(explodeStageText(0.6, 4)).toBe('Separating structures');
    expect(explodeStageText(1, 4)).toBe('Every piece apart');
  });
  it('steps systems apart first, then every piece', () => {
    expect(nextExplodeStop(0, 4)).toBe(SYSTEM_SEPARATION_END);
    expect(nextExplodeStop(0.31, 4)).toBe(1);
    expect(nextExplodeStop(0, 1)).toBe(1);
  });
});

describe('playback', () => {
  const plan = planExplodePlayback(0, 4);
  it('runs two legs with a hold between them, ending on every piece', () => {
    expect(plan.legs.map((l) => l.to)).toEqual([SYSTEM_SEPARATION_END, 1]);
    const first = plan.legs[0].ms;
    expect(explodePlaybackAt(plan, 0).amount).toBe(0);
    expect(explodePlaybackAt(plan, first).amount).toBeCloseTo(SYSTEM_SEPARATION_END, 10);
    expect(explodePlaybackAt(plan, first + 200).amount).toBeCloseTo(SYSTEM_SEPARATION_END, 10); // holding
    expect(explodePlaybackAt(plan, 1e6)).toEqual({ amount: 1, done: true });
    expect(explodePlaybackAt(plan, first + 200).done).toBe(false);
  });
  it('never goes backwards and is continuous', () => {
    let last = 0;
    for (let ms = 0; ms < 4000; ms += 16) {
      const a = explodePlaybackAt(plan, ms).amount;
      expect(a).toBeGreaterThanOrEqual(last - 1e-12);
      expect(a - last).toBeLessThan(0.05);
      last = a;
    }
  });
  it('resumes from the current amount and restarts from assembled when already apart', () => {
    expect(planExplodePlayback(0.6, 4).legs.map((l) => l.to)).toEqual([1]);
    expect(planExplodePlayback(1, 4).from).toBe(0);
    expect(planExplodePlayback(1, 4).legs).toHaveLength(2);
    expect(planExplodePlayback(0.6, 4).legs[0].ms).toBeGreaterThanOrEqual(400);
  });
});
