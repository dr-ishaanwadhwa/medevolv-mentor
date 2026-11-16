import { describe, expect, it } from 'vitest';
import { COPY, askInstead, diagramUx, loadingCopy } from './diagram';

describe('diagram copy map (PRD 4.1 UX table, D-17)', () => {
  it('validator decline: not-enough copy, ask chip, no Retry', () => {
    const ux = diagramUx({ kind: 'declined', reason: 'too_few_supported_nodes' });
    expect(ux).toMatchObject({ copy: COPY.notEnough, retry: false, askChip: true, hideChip: false, chipLock: 'none' });
  });
  it('generator_error: "Couldn\'t draw it right now." with Retry', () => {
    expect(diagramUx({ kind: 'declined', reason: 'generator_error' })).toMatchObject({ copy: COPY.failed, retry: true });
  });
  it('budget: paused copy, no Retry, chip disabled for the page with "Paused for today"', () => {
    expect(diagramUx({ kind: 'declined', reason: 'budget' })).toMatchObject({
      copy: 'Flowcharts are paused for today.',
      retry: false,
      chipLock: 'page',
      lockTip: 'Paused for today',
    });
  });
  it('429: rate-limit copy, no Retry, chip locked for a minute', () => {
    expect(diagramUx({ kind: 'http', status: 429 })).toMatchObject({
      copy: 'Too many requests, try again in a minute.',
      retry: false,
      chipLock: 'minute',
    });
  });
  it.each([403, 503])('%i: card and chip removed, no text', (status) => {
    expect(diagramUx({ kind: 'http', status })).toMatchObject({ copy: null, hideChip: true });
  });
  it.each([{ kind: 'abort' as const }, { kind: 'network' as const }])('$kind: failed copy with Retry', (o) => {
    expect(diagramUx(o)).toMatchObject({ copy: COPY.failed, retry: true, hideChip: false });
  });
  it('unknown future reason: failed copy without Retry', () => {
    expect(diagramUx({ kind: 'declined', reason: 'something_new' })).toMatchObject({ copy: COPY.failed, retry: false });
  });
  it('patient_scoped from the server removes the card quietly', () => {
    expect(diagramUx({ kind: 'declined', reason: 'patient_scoped' })).toMatchObject({ copy: null, hideChip: true });
  });
  it('loading copy names the citation range', () => {
    expect(loadingCopy(4)).toBe('Drawing a flowchart from citations [1]-[4]...');
    expect(loadingCopy(0)).toBe('Drawing a flowchart from the citations...');
  });
  it('tap-to-ask only with a subject', () => {
    expect(askInstead('beta blockers')).toBe('Classify beta blockers');
    expect(askInstead(null)).toBeNull();
    expect(askInstead('  ')).toBeNull();
  });
});
