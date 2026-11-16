import { describe, expect, it } from 'vitest';
import { returningRedirect } from './returning';

const q = (s: string) => new URLSearchParams(s);

describe('returning-user redirect (D-5)', () => {
  it('sends a returning asker from / to /ask', () => {
    expect(returningRedirect('/', q(''), '1')).toBe('/ask');
  });
  it('shows the landing to a new browser', () => {
    expect(returningRedirect('/', q(''), undefined)).toBeNull();
  });
  it('?tour=1 always shows the landing', () => {
    expect(returningRedirect('/', q('tour=1'), '1')).toBeNull();
  });
  it('leaves /?q= to the next.config redirect, so the query survives', () => {
    expect(returningRedirect('/', q('q=x&go=1'), '1')).toBeNull();
  });
  it('never touches other paths', () => {
    expect(returningRedirect('/ask', q(''), '1')).toBeNull();
    expect(returningRedirect('/how', q(''), '1')).toBeNull();
  });
});
