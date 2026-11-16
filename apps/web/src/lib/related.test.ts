import { describe, expect, it } from 'vitest';
import { askHref, relatedQuestion } from './related';

describe('related topics', () => {
  it('asks the certified label itself', () => {
    expect(relatedQuestion('  Minimal   change disease ')).toBe('Minimal change disease');
  });
  it('shared pages open Ask with the question and send it', () => {
    expect(askHref('Minimal change disease')).toBe('/ask?q=Minimal+change+disease&go=1');
  });
});
