import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { buildIndex, normalizeFma, resolveHighlight, SYSTEMS, DEFAULT_VISIBLE, type Atlas } from './anatomy';

const part = (id: string, conceptId: string, system: Atlas['parts'][number]['system']) => ({
  id, name: id, conceptId, system, chunk: 0, positions: 0, normals: 0, indices: 0, vertexCount: 3, indexCount: 3,
  bounds: [[0, 0, 0], [1, 1, 1]] as [number[], number[]],
});
const mini: Atlas = {
  version: 'test', sex: 'female', triangles: 3, chunks: [],
  parts: [
    part('VHF:BODY_OF_UTERUS', 'UBERON:0009853', 'reproductive_female'),
    part('VHF:LEFT_OVARY', 'FMA7214', 'reproductive_female'),
    part('VHF:CERVIX_X', 'HRA:VH_F_CERVIX_X', 'reproductive_female'),
    part('VHF:PLACENTA', 'HRA:VH_F_PLACENTA', 'pregnancy'),
  ],
  concepts: [
    { id: 'UBERON:0009853', name: 'body of uterus', elements: ['VHF:BODY_OF_UTERUS'] },
    { id: 'HRA:VH_F_UTERUS', name: 'uterus', elements: ['VHF:BODY_OF_UTERUS', 'VHF:CERVIX_X'] },
  ],
};

describe('female ids survive the matchers', () => {
  const index = buildIndex(mini);
  it('normalizeFma keeps UBERON and HRA ids intact apart from case', () => {
    expect(normalizeFma(' uberon:0009853 ')).toBe('UBERON:0009853');
    expect(normalizeFma('hra:vh_f_uterus')).toBe('HRA:VH_F_UTERUS');
    expect(normalizeFma('7214')).toBe('FMA7214');
  });
  it('resolves FMA, UBERON, synthetic and compound ids, in any case', () => {
    for (const id of ['FMA7214', 'fma7214', 'UBERON:0009853', 'uberon:0009853', 'HRA:VH_F_CERVIX_X', 'hra:vh_f_cervix_x']) {
      expect(resolveHighlight(mini, index, [id]).unmatched, id).toEqual([]);
    }
    const uterus = resolveHighlight(mini, index, ['HRA:VH_F_UTERUS']);
    expect(uterus.partIdx).toEqual([0, 2]);
  });
  it('a male-only id is unmatched in the female atlas', () => {
    expect(resolveHighlight(mini, index, ['FMA7088']).unmatched).toEqual(['FMA7088']);
  });
});

describe('systems', () => {
  it('declares the two female systems; pregnancy is hidden by default', () => {
    const ids = SYSTEMS.map((s) => s.id);
    expect(ids).toContain('reproductive_female');
    expect(ids).toContain('pregnancy');
    expect(DEFAULT_VISIBLE).toContain('reproductive_female');
    expect(DEFAULT_VISIBLE).not.toContain('pregnancy');
  });
});

// Runs only on a machine that has built the female model (deploy/atlas/female/build_female.sh).
const built = path.join(os.homedir(), 'Projects/third_party/human-atlas/public/models/female.json');
describe.skipIf(!fs.existsSync(built))('built female.json', () => {
  const atlas = JSON.parse(fs.readFileSync(built, 'utf8')) as Atlas;
  const index = buildIndex(atlas);
  const ids = atlas.concepts.map((c) => c.id);
  it('every concept id and every part concept id resolves, uppercase, without spaces or commas', () => {
    expect(resolveHighlight(atlas, index, ids).unmatched).toEqual([]);
    for (const id of [...ids, ...atlas.parts.map((p) => p.conceptId)]) expect(id).toMatch(/^[^\s,a-z]+$/);
  });
  it('every system used is declared', () => {
    const declared = new Set(SYSTEMS.map((s) => s.id));
    for (const p of atlas.parts) expect(declared.has(p.system), p.system).toBe(true);
  });
  it('uterus, ovary and cervix are findable', () => {
    for (const id of ['HRA:VH_F_UTERUS', 'FMA7214', 'FMA7213', 'UBERON:0000002']) {
      expect(resolveHighlight(atlas, index, [id]).matched, id).toEqual([id]);
    }
  });
});
