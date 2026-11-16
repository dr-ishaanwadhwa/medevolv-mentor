import { describe, expect, it } from 'vitest';
import type { Atlas } from './anatomy';
import {
  autoSwitchTarget,
  decideTarget,
  defaultFramingParts,
  gzipTotalBytes,
  indexOf,
  isConstrainedConnection,
  manifestCacheKey,
  manifestMatches,
  milestoneCrossed,
  parseSex,
  partitionSelection,
  progressText,
  readFemaleConfirmed,
  readSexPreference,
  withSex,
  withSexAndSelection,
  writeFemaleConfirmed,
  writeSexPreference,
} from './atlas-sex';
import { atlasHref } from './format';

const part = (id: string, conceptId: string, system: string, name = id) => ({
  id,
  name,
  conceptId,
  system,
  chunk: 0,
  positions: 0,
  normals: 0,
  indices: 0,
  vertexCount: 0,
  indexCount: 0,
  bounds: [[0, 0, 0], [1, 1, 1]] as [number[], number[]],
});

const male = {
  version: 'm',
  sex: 'male',
  parts: [part('P1', 'FMA13303', 'skeletal', 'humerus'), part('P2', 'FMA7088', 'cardiovascular', 'heart')],
  concepts: [
    { id: 'FMA13303', name: 'humerus', elements: ['P1'] },
    { id: 'FMA7088', name: 'heart', elements: ['P2'] },
  ],
  chunks: [{ url: '/models/body-0.bin', bytes: 10, gzip: '/models/body-0.bin.gz', gzipBytes: 4 }],
  triangles: 2,
} as unknown as Atlas;

const female = {
  version: 'f',
  sex: 'female',
  parts: [
    part('F1', 'HRA:VH_F_UTERUS_BODY', 'reproductive_female', 'body of uterus'),
    part('F2', 'FMA7088', 'cardiovascular', 'heart'),
    part('F3', 'UBERON:0001270', 'skeletal', 'pubis'),
    part('F4', 'HRA:VH_F_PLACENTA', 'pregnancy', 'placenta'),
    part('F5', 'FMA1', 'urinary', 'bladder'),
  ],
  concepts: [
    { id: 'HRA:VH_F_UTERUS_BODY', name: 'body of uterus', elements: ['F1'] },
    { id: 'FMA7088', name: 'heart', elements: ['F2'] },
    { id: 'UBERON:0001270', name: 'pubis', elements: ['F3'] },
  ],
  chunks: [
    { url: '/models/female-0.bin', bytes: 10, gzip: '/models/female-0.bin.gz', gzipBytes: 3_000_000 },
    { url: '/models/female-1.bin', bytes: 2_000_000 },
  ],
  triangles: 5,
} as unknown as Atlas;

describe('parseSex / decideTarget (F-2, F-9)', () => {
  it('parses only male and female', () => {
    expect(parseSex('Female')).toBe('female');
    expect(parseSex('male')).toBe('male');
    expect(parseSex('x')).toBeNull();
    expect(parseSex(null)).toBeNull();
  });
  it('flag off: always male and the sex param is stripped', () => {
    expect(decideTarget({ param: 'female', hasSelect: false, flag: false, stored: 'female' })).toEqual({
      target: 'male',
      stripParam: true,
      fromStored: false,
    });
    expect(decideTarget({ param: null, hasSelect: false, flag: false, stored: null }).stripParam).toBe(false);
  });
  it('flag on: ?sex= wins, then a ?select= link beats the stored preference, then the stored one', () => {
    expect(decideTarget({ param: 'female', hasSelect: true, flag: true, stored: 'male' }).target).toBe('female');
    expect(decideTarget({ param: null, hasSelect: true, flag: true, stored: 'female' }).target).toBe('male');
    expect(decideTarget({ param: null, hasSelect: false, flag: true, stored: 'female' })).toEqual({
      target: 'female',
      stripParam: false,
      fromStored: true,
    });
    expect(decideTarget({ param: null, hasSelect: false, flag: true, stored: null }).target).toBe('male');
  });
});

describe('URL helpers keep other params', () => {
  it('withSex sets, replaces and removes sex, keeping select readable', () => {
    expect(withSex('?select=FMA1,FMA2', 'female')).toBe('?select=FMA1,FMA2&sex=female');
    expect(withSex('?select=FMA1&sex=female&x=1', 'male')).toBe('?select=FMA1&x=1&sex=male');
    expect(withSex('?sex=female', null)).toBe('');
    expect(withSex('?select=FMA1&sex=female', null)).toBe('?select=FMA1');
  });
  it('withSexAndSelection replaces both and keeps the rest', () => {
    expect(withSexAndSelection('?select=FMA1&sex=male&x=1', 'female', ['HRA:VH_F_UTERUS_BODY'])).toBe(
      '?select=HRA%3AVH_F_UTERUS_BODY&sex=female&x=1',
    );
    expect(withSexAndSelection('?select=FMA1&sex=female', 'male', [])).toBe('?sex=male');
  });
  it('atlasHref adds &sex=female only for a female structure with the flag on', () => {
    expect(atlasHref(['FMA1'])).toBe('/atlas?select=FMA1');
    expect(atlasHref(['UBERON:0000995'], { sex: 'female', femaleAtlas: false })).toBe('/atlas?select=UBERON:0000995');
    expect(atlasHref(['UBERON:0000995'], { sex: 'female', femaleAtlas: true })).toBe('/atlas?select=UBERON:0000995&sex=female');
    expect(atlasHref(['FMA1'], { sex: 'male', femaleAtlas: true })).toBe('/atlas?select=FMA1');
  });
});

describe('manifest identity (F-1a)', () => {
  it('per-sex cache keys', () => {
    expect(manifestCacheKey('male')).toBe('atlas.json:male');
    expect(manifestCacheKey('female')).toBe('atlas.json:female');
  });
  it('a male manifest never passes as female, and the reverse', () => {
    expect(manifestMatches('female', male)).toBe(false);
    expect(manifestMatches('male', female)).toBe(false);
    expect(manifestMatches('female', female)).toBe(true);
    expect(manifestMatches('male', male)).toBe(true);
    expect(manifestMatches('male', { ...male, sex: undefined })).toBe(true); // older male builds had no sex field
    expect(manifestMatches('male', null)).toBe(false);
  });
});

describe('selection across models (F-3)', () => {
  const mi = indexOf(male);
  const fi = indexOf(female);
  it('keeps ids present in the target by concept id and drops the rest', () => {
    expect(partitionSelection(['FMA7088', 'HRA:VH_F_UTERUS_BODY'], male, mi)).toEqual({
      keep: ['FMA7088'],
      dropped: ['HRA:VH_F_UTERUS_BODY'],
    });
  });
  it('matches HRA and UBERON ids in any case', () => {
    expect(partitionSelection(['hra:vh_f_uterus_body', 'uberon:0001270'], female, fi).keep).toHaveLength(2);
  });
  it('auto-switches symmetrically, and only when nothing is found in the current model', () => {
    const m = { atlas: male, index: mi };
    const f = { atlas: female, index: fi };
    expect(autoSwitchTarget('male', ['HRA:VH_F_UTERUS_BODY'], m, f)).toBe('female');
    expect(autoSwitchTarget('female', ['FMA13303'], f, m)).toBe('male');
    expect(autoSwitchTarget('male', ['FMA7088', 'HRA:VH_F_UTERUS_BODY'], m, f)).toBeNull();
    expect(autoSwitchTarget('male', ['FMA999999'], m, f)).toBeNull();
    expect(autoSwitchTarget('male', ['HRA:VH_F_UTERUS_BODY'], m, null)).toBeNull();
    expect(autoSwitchTarget('male', [], m, f)).toBeNull();
  });
});

describe('default view per model', () => {
  it('male frames the whole body (null), female the reproductive, urinary and pelvic parts only', () => {
    expect(defaultFramingParts(male, 'male')).toBeNull();
    expect(defaultFramingParts(female, 'female')).toEqual([0, 2, 4]); // never the hidden pregnancy part
  });
});

describe('download size and progress', () => {
  it('sums gzip bytes, falling back to raw bytes', () => {
    expect(gzipTotalBytes(female)).toBe(5_000_000);
    expect(gzipTotalBytes(null)).toBe(0);
    expect(progressText(50, 30_000_000)).toBe('15 of 30 MB');
  });
  it('announces only quarter milestones', () => {
    expect(milestoneCrossed(0, 10)).toBeNull();
    expect(milestoneCrossed(20, 30)).toBe(25);
    expect(milestoneCrossed(40, 80)).toBe(75);
    expect(milestoneCrossed(80, 100)).toBeNull();
  });
  it('treats Save-Data and 2g/3g as constrained', () => {
    expect(isConstrainedConnection({ saveData: true })).toBe(true);
    expect(isConstrainedConnection({ effectiveType: '3g' })).toBe(true);
    expect(isConstrainedConnection({ effectiveType: '4g' })).toBe(false);
    expect(isConstrainedConnection(undefined)).toBe(false);
  });
});

describe('per-browser preference', () => {
  it('round-trips and survives a throwing storage', () => {
    const m = new Map<string, string>();
    const store = { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v) };
    expect(readSexPreference(store)).toBeNull();
    writeSexPreference('female', store);
    expect(readSexPreference(store)).toBe('female');
    expect(readFemaleConfirmed(store)).toBe(false);
    writeFemaleConfirmed(store);
    expect(readFemaleConfirmed(store)).toBe(true);
    const bad = {
      getItem: () => {
        throw new Error('blocked');
      },
      setItem: () => {
        throw new Error('blocked');
      },
    };
    expect(readSexPreference(bad)).toBeNull();
    expect(() => writeSexPreference('male', bad)).not.toThrow();
  });
});
