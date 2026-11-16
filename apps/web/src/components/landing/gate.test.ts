import { describe, expect, it } from 'vitest';
import { mapCaption, reducedSceneState, sceneState, staticReason } from './gate';

describe('landing stage gate (L-5, fallbacks)', () => {
  it('stays static without WebGL, on Save-Data and on 2g, and only then', () => {
    expect(staticReason({ webgl: false })).toBe('no-webgl');
    expect(staticReason({ webgl: true, saveData: true })).toBe('save-data');
    expect(staticReason({ webgl: true, effectiveType: 'slow-2g' })).toBe('slow-connection');
    expect(staticReason({ webgl: true, effectiveType: '2g' })).toBe('slow-connection');
    expect(staticReason({ webgl: true, effectiveType: '4g' })).toBeNull();
    expect(staticReason({ webgl: true })).toBeNull(); // iOS: no navigator.connection, the 6 s time fallback covers it
  });
});

describe('map caption (L-12)', () => {
  it('states the rendered count on phones', () => {
    expect(mapCaption(12300, 36725)).toBe('Each dot is a passage. Showing 12,300 of 36,725 on this screen.');
  });
  it('states the total when every point renders', () => {
    expect(mapCaption(36725, 36725)).toBe('36,725 passages. Each dot is one.');
  });
});

describe('scene states', () => {
  it('the decline dims the map, the body scene shows the chiasm', () => {
    expect(sceneState(0).dim).toBeCloseTo(1);
    expect(sceneState(2.2).dim).toBeLessThan(0.4);
    expect(sceneState(0).chiasm).toBeCloseTo(0);
    expect(sceneState(3.1).chiasm).toBeCloseTo(1);
  });
  it('reduced motion snaps to scene end states (no in-between blends)', () => {
    expect(reducedSceneState(2.4)).toEqual(reducedSceneState(2));
    expect(reducedSceneState(2.6)).toEqual(reducedSceneState(3));
    expect(reducedSceneState(9)).toEqual(reducedSceneState(4));
  });
});
