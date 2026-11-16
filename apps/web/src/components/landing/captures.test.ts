import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { PATIENT_SCOPED } from './facts';
import { citeLabel, citedBookIndexes, declined, heroAnswer, journey, why } from './captures';

const raw = (n: string) => readFileSync(fileURLToPath(new URL(`../../../public/landing/${n}.json`, import.meta.url)), 'utf8');

describe('landing captures', () => {
  it('carry pointers only: no excerpt or passage field, with capture date and commit', () => {
    for (const n of ['journey', 'declined', 'why']) {
      const t = raw(n);
      expect(t, n).not.toContain('"excerpt"');
      const d = JSON.parse(t);
      expect(d.captured_at, n).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(d.commit, n).toMatch(/^[0-9a-f]{7,}$/);
    }
  });

  it('the hero question and the why question are not patient-scoped, and the journey was answered', () => {
    expect(PATIENT_SCOPED.test(journey.question)).toBe(false);
    expect(PATIENT_SCOPED.test(why.question)).toBe(false);
    expect(journey.status).toBe('answered');
    expect(declined.status).not.toBe('answered');
  });

  it('the why capture picked a wrong option and has three viva questions', () => {
    expect(why.verdict.correct_option).not.toBe(why.chosen);
    expect(why.verdict.viva_questions).toHaveLength(3);
  });

  it('hero answer is two sentences and its pointers are cited ones', () => {
    const h = heroAnswer(journey.answer, journey.citations);
    expect(h.sentences).toHaveLength(2);
    expect(h.used.length).toBeGreaterThan(0);
    expect(h.used.every((c) => c.cited)).toBe(true);
    for (const c of h.used) expect(citeLabel(c)).toMatch(/ · Ch \d+ · pp /);
  });

  it('maps cited books to story.json indexes', () => {
    expect(citedBookIndexes(journey.citations).length).toBeGreaterThan(0);
  });
});
