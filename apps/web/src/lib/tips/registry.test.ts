import { describe, expect, it } from 'vitest';
import { TIPS, TIP_SOURCES } from './index';
import type { Tip } from './types';

// Guards the merged registry (PRD R3): a spread silently drops an id defined in two feature files,
// and an empty or copy-pasted tip reads as noise to the student.
const sources = Object.entries(TIP_SOURCES) as [string, Record<string, Tip>][];

describe('tips registry integrity', () => {
  it('no entry is empty', () => {
    for (const [id, t] of Object.entries(TIPS) as [string, Tip][]) {
      expect(typeof t.purpose, id).toBe('string');
      expect(typeof t.effect, id).toBe('string');
      expect(t.purpose.trim(), `${id} purpose`).not.toBe('');
      expect(t.effect.trim(), `${id} effect`).not.toBe('');
      if ('disabled' in t) expect((t.disabled ?? '').trim(), `${id} disabled`).not.toBe('');
    }
  });

  it('no id is defined in two feature files', () => {
    const owner = new Map<string, string>();
    const dupes: string[] = [];
    for (const [file, tips] of sources) {
      for (const id of Object.keys(tips)) {
        if (owner.has(id)) dupes.push(`${id} (${owner.get(id)} and ${file})`);
        owner.set(id, file);
      }
    }
    expect(dupes).toEqual([]);
    expect(Object.keys(TIPS).length).toBe(owner.size);
  });

  it('every feature file is merged, and its ids carry its own prefix', () => {
    for (const [file, tips] of sources) {
      for (const id of Object.keys(tips)) {
        expect(id.startsWith(`${file}.`), `${id} lives in ${file}.ts`).toBe(true);
        expect(TIPS).toHaveProperty([id]);
      }
    }
  });

  it('no two ids share the same copy', () => {
    const seen = new Map<string, string>();
    const dupes: string[] = [];
    for (const [id, t] of Object.entries(TIPS) as [string, Tip][]) {
      const key = `${t.purpose.trim().toLowerCase()}|${t.effect.trim().toLowerCase()}`;
      if (seen.has(key)) dupes.push(`${id} repeats ${seen.get(key)}`);
      else seen.set(key, id);
    }
    expect(dupes).toEqual([]);
  });

  it('every entry is at most 26 words (PRD: plain words, short)', () => {
    for (const [id, t] of Object.entries(TIPS) as [string, Tip][]) {
      expect(`${t.purpose} ${t.effect}`.split(/\s+/).length, id).toBeLessThanOrEqual(26);
    }
  });
});
