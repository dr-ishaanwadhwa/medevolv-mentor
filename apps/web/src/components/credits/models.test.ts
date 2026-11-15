import { describe, expect, it } from 'vitest';
import { CC_BY_URL, MODELS, MODEL_ORDER } from './models';

describe('model credits', () => {
  it('has title, version, source, licence and changes for every model', () => {
    for (const id of MODEL_ORDER) {
      const m = MODELS[id];
      expect(m.id).toBe(id);
      for (const f of [m.title, m.version, m.creators, m.short, m.changes]) expect(f.length).toBeGreaterThan(5);
      expect(m.sourceUrl).toMatch(/^https:\/\//);
      expect(m.licenseUrl).toBe(CC_BY_URL);
      expect(m.short).toContain('CC BY 4.0');
    }
  });
});
