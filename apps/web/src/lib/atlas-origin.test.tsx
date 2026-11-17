// Female study model honesty (ADR-003): the switch says "study model", its tip says male-derived, and every selected
// structure is labelled native HRA female data or reshaped male geometry.
import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { renderToStaticMarkup } from 'react-dom/server';
import { buildIndex, type Atlas } from './anatomy';
import { FEMALE_NOTE, originLabel, originOf, SEX_TOGGLE_LABEL } from './atlas-sex';
import { ATLAS_TIPS } from './tips/atlas';
import { SexToggle, FemaleNote } from '@/components/canvas/SexToggle';

const part = (id: string, conceptId: string, origin?: 'hra-female' | 'bp3d-reshaped') => ({
  id, name: id, conceptId, system: 'skeletal' as const, chunk: 0, positions: 0, normals: 0, indices: 0,
  vertexCount: 3, indexCount: 3, bounds: [[0, 0, 0], [1, 1, 1]] as [number[], number[]], ...(origin ? { origin } : {}),
});

const study: Atlas = {
  version: 'female-study-v3@test', sex: 'female', triangles: 3, chunks: [],
  parts: [
    part('VH_F_body_of_uterus', 'UBERON:0009853', 'hra-female'),
    part('VH_F_cervix', 'UBERON:0000002', 'hra-female'),
    part('FJ3259', 'FMA9611', 'bp3d-reshaped'), // femur
    part('VH_F_sacrum', 'UBERON:0003690', 'hra-female'),
    part('FJ3200', 'FMA13478', 'bp3d-reshaped'), // a vertebra
  ],
  concepts: [
    { id: 'HRA:VH_F_UTERUS', name: 'uterus', elements: ['VH_F_body_of_uterus', 'VH_F_cervix'] },
    { id: 'FMA9611', name: 'femur', elements: ['FJ3259'] },
    { id: 'FMA23881', name: 'skeletal system', elements: ['FJ3259', 'VH_F_sacrum', 'FJ3200'] },
  ],
};
const male: Atlas = { ...study, version: 'm', sex: 'male', parts: study.parts.map(({ origin: _o, ...p }) => p) };

describe('part origin (study model)', () => {
  const idx = buildIndex(study);
  it('native HRA, reshaped male and mixed', () => {
    expect(originOf(study, idx, 'HRA:VH_F_UTERUS')).toBe('hra-female');
    expect(originOf(study, idx, 'hra:vh_f_uterus')).toBe('hra-female');
    expect(originOf(study, idx, 'FMA9611')).toBe('bp3d-reshaped');
    expect(originOf(study, idx, 'FMA23881')).toBe('mixed');
  });
  it('nothing for an id the model does not draw, or a model without origin data', () => {
    expect(originOf(study, idx, 'FMA7088')).toBeNull();
    expect(originOf(male, buildIndex(male), 'FMA9611')).toBeNull();
    expect(originOf(null, null, 'FMA9611')).toBeNull();
  });
  it('labels: a reshaped part never reads as female anatomy', () => {
    expect(originLabel('bp3d-reshaped')).toMatch(/reshaped from the male model/i);
    expect(originLabel('bp3d-reshaped')).toMatch(/not female anatomy data/i);
    expect(originLabel('hra-female')).toMatch(/Human Reference Atlas/);
    expect(originLabel('mixed')).toMatch(/partly reshaped/i);
  });
});

describe('Female (study model) switch', () => {
  it('label, tooltip and note say male-derived, HRA organs, orientation only', () => {
    expect(SEX_TOGGLE_LABEL.female).toBe('Female (study model)');
    const tip = ATLAS_TIPS['atlas.sex.female'];
    expect(`${tip.purpose} ${tip.effect}`).toMatch(/male-derived body reshaped to a female form/);
    expect(`${tip.purpose} ${tip.effect}`).toMatch(/Human Reference Atlas/);
    expect(`${tip.purpose} ${tip.effect}`).toMatch(/orientation only/);
    expect(FEMALE_NOTE).toMatch(/male body reshaped to a female form/);
    expect(FEMALE_NOTE).toMatch(/orientation only/);
    expect(FEMALE_NOTE.split(/[.!?](\s|$)/).filter((x) => x && x.trim()).length).toBe(1); // one short sentence
  });
  it('renders the radios with the new label', () => {
    const html = renderToStaticMarkup(<SexToggle value="female" onChange={() => {}} />);
    expect(html).toContain('Female (study model)');
    expect(html).toContain('aria-checked="true"');
    expect(html).not.toContain('Female (organs)');
    expect(renderToStaticMarkup(<FemaleNote id="n" />)).toContain('for orientation only');
  });
});

// Runs only where build_atlas.sh installed the study model into the human-atlas clone.
const built = path.join(os.homedir(), 'Projects/third_party/human-atlas/public/models/female.json');
const isStudy = fs.existsSync(built) && fs.readFileSync(built, 'utf8').slice(0, 200).includes('female-study-v3');
describe.skipIf(!isStudy)('installed study female.json', () => {
  const atlas = JSON.parse(fs.readFileSync(built, 'utf8')) as Atlas;
  const idx = buildIndex(atlas);
  it('every part has an origin: 64 HRA female, 2,181 reshaped', () => {
    const n = (o: string) => atlas.parts.filter((p) => p.origin === o).length;
    expect(n('hra-female')).toBe(64);
    expect(n('bp3d-reshaped')).toBe(2181);
  });
  it('female-only structures are native, a femur is reshaped', () => {
    for (const id of ['HRA:VH_F_UTERUS', 'FMA7214', 'FMA7213', 'UBERON:0000002', 'HRA:VH_F_FALLOPIAN_TUBE']) {
      expect(originOf(atlas, idx, id), id).toBe('hra-female');
    }
    expect(originOf(atlas, idx, 'FMA9611')).toBe('bp3d-reshaped');
  });
});
