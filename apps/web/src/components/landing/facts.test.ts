import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { BOOK_SHORT, EVAL_CAVEAT, EXAMPLES, FACTS, NOT_YET, PATIENT_SCOPED, coverage, editionShort } from './facts';

describe('landing facts (L-7)', () => {
  it('every number has a source, a date, a sample and a caveat', () => {
    for (const f of Object.values(FACTS)) {
      expect(f.source.length, f.id).toBeGreaterThan(5);
      expect(f.date, f.id).toMatch(/\d{4}|\d{1,2} \w{3} \d{4}/);
      expect(f.sample.length, f.id).toBeGreaterThan(3);
      expect(f.caveats.length, f.id).toBeGreaterThan(0);
    }
  });

  it('the eval caveat is word for word the one on /how', () => {
    const story = readFileSync(fileURLToPath(new URL('../story/Story.tsx', import.meta.url)), 'utf8');
    expect(story).toContain(EVAL_CAVEAT);
  });

  it('the behaviour fact is labelled internal and carries the limitation line', () => {
    expect(FACTS.behaviour.sample).toMatch(/internal/);
    expect(FACTS.behaviour.caveats.join(' ')).toMatch(/patient care/);
  });

  it('passage and book counts come from story.json', () => {
    expect(FACTS.passages.value).toBe('36,725');
    expect(FACTS.books.value).toBe('7');
  });

  it('coverage groups every book once and never lists a covered subject as missing', () => {
    const groups = coverage();
    const ids = groups.flatMap((g) => g.books.map((b) => b.id));
    expect(new Set(ids).size).toBe(7);
    expect(ids.every((id) => id in BOOK_SHORT)).toBe(true);
    for (const g of groups) expect(NOT_YET as readonly string[]).not.toContain(g.subject);
    expect(groups.find((g) => g.subject === 'Medicine')?.books.length).toBe(2);
  });

  it('parses editions from titles', () => {
    expect(editionShort("Davidson's Principles and Practice of Medicine (24th ed.)")).toBe('24e');
    expect(editionShort('Essentials of Medical Microbiology')).toBe('');
  });

  it('examples are exam or viva questions, never patient-scoped (L-7a)', () => {
    expect(EXAMPLES).toHaveLength(3);
    for (const e of EXAMPLES) expect(PATIENT_SCOPED.test(e.q), e.q).toBe(false);
    expect(PATIENT_SCOPED.test('A patient with pheochromocytoma is posted for surgery. What drug should be started first?')).toBe(true);
    expect(PATIENT_SCOPED.test('My mother has TB, what dose should she take?')).toBe(true);
  });
});
