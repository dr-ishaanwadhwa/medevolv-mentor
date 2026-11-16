import { describe, expect, it } from 'vitest';
import { ANSWER_TIPS } from './answer';

describe('answer tips', () => {
  it.each(Object.entries(ANSWER_TIPS))('%s has purpose and effect, at most 26 words', (_id, tip) => {
    expect(tip.purpose.trim()).not.toBe('');
    expect(tip.effect.trim()).not.toBe('');
    expect(`${tip.purpose} ${tip.effect}`.split(/\s+/).length).toBeLessThanOrEqual(26);
  });
});
