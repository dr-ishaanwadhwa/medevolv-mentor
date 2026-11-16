import { describe, expect, it } from 'vitest';
import * as T from 'three';
import { pinchZoomFactor, wheelZoomFactor, zoomAnchor, zoomTowardPoint } from './atlas-zoom';

const v = (x: number, y: number, z: number) => new T.Vector3(x, y, z);
const view = (position: T.Vector3, target: T.Vector3) => {
  const camera = new T.PerspectiveCamera(34, 1.25, 0.005, 100);
  camera.position.copy(position);
  camera.lookAt(target);
  camera.updateMatrixWorld();
  camera.updateProjectionMatrix();
  return camera;
};
const screenOf = (camera: T.PerspectiveCamera, p: T.Vector3) => p.clone().project(camera);

describe('wheelZoomFactor', () => {
  it('zooms in for a forward scroll and out for a backward one', () => {
    expect(wheelZoomFactor(-100)).toBeLessThan(1);
    expect(wheelZoomFactor(100)).toBeGreaterThan(1);
    expect(wheelZoomFactor(0)).toBe(1);
  });
  it('is symmetric and capped per event', () => {
    expect(wheelZoomFactor(120) * wheelZoomFactor(-120)).toBeCloseTo(1, 10);
    expect(wheelZoomFactor(1e6)).toBeLessThanOrEqual(1.6);
    expect(wheelZoomFactor(-1e6)).toBeGreaterThanOrEqual(1 / 1.6);
  });
  it('gives touchpad pinch (ctrl+wheel) and line-mode wheels a usable gain', () => {
    expect(wheelZoomFactor(-4, 0, true)).toBeLessThan(wheelZoomFactor(-4, 0, false));
    expect(wheelZoomFactor(-3, 1)).toBeCloseTo(wheelZoomFactor(-48, 0), 10);
  });
});

describe('pinchZoomFactor', () => {
  it('fingers apart brings the camera closer by the same ratio', () => {
    expect(pinchZoomFactor(100, 200)).toBeCloseTo(0.625, 10); // 0.5 capped to 1/1.6
    expect(pinchZoomFactor(100, 125)).toBeCloseTo(0.8, 10);
    expect(pinchZoomFactor(125, 100)).toBeCloseTo(1.25, 10);
  });
  it('ignores a degenerate span', () => {
    expect(pinchZoomFactor(0, 50)).toBe(1);
    expect(pinchZoomFactor(50, NaN)).toBe(1);
  });
});

describe('zoomTowardPoint', () => {
  const position = v(0, 1, 4);
  const target = v(0, 1, 0);
  const ray = new T.Ray(position.clone(), v(0, 0, -1));
  const limits = { minDistance: 0.06, maxDistance: 30 };

  it('keeps the point under the cursor at the same screen position', () => {
    const hit = v(0.3, 1.2, 0.5); // off-axis surface point under the cursor
    const before = screenOf(view(position, target), hit);
    const next = zoomTowardPoint({ position, target, ray, hit, factor: 0.5, ...limits });
    const after = screenOf(view(next.position, next.target), hit);
    expect(after.x).toBeCloseTo(before.x, 6);
    expect(after.y).toBeCloseTo(before.y, 6);
    expect(next.position.distanceTo(next.target)).toBeCloseTo(2, 10);
  });

  it('zooming out keeps it there too', () => {
    const hit = v(-0.4, 0.7, 0.2);
    const before = screenOf(view(position, target), hit);
    const next = zoomTowardPoint({ position, target, ray, hit, factor: 1.4, ...limits });
    const after = screenOf(view(next.position, next.target), hit);
    expect(after.x).toBeCloseTo(before.x, 6);
    expect(after.y).toBeCloseTo(before.y, 6);
  });

  it('on empty space it anchors on the plane through the target, so the ray point stays put', () => {
    const r = new T.Ray(position.clone(), v(0.2, 0, -1).normalize());
    const anchor = zoomAnchor(position, target, r, null);
    expect(anchor.z).toBeCloseTo(0, 10); // the plane through the target, facing the camera
    const before = screenOf(view(position, target), anchor);
    const next = zoomTowardPoint({ position, target, ray: r, hit: null, factor: 0.7, ...limits });
    const after = screenOf(view(next.position, next.target), anchor);
    expect(after.x).toBeCloseTo(before.x, 6);
    expect(after.y).toBeCloseTo(before.y, 6);
  });

  it('a cursor on the view axis zooms straight towards the target', () => {
    const next = zoomTowardPoint({ position, target, ray, hit: null, factor: 0.5, ...limits });
    expect(next.target.distanceTo(target)).toBeLessThan(1e-9);
    expect(next.position.z).toBeCloseTo(2, 10);
  });

  it('clamps to the distance limits and stops there', () => {
    const near = zoomTowardPoint({ position, target, ray, hit: null, factor: 1e-6, ...limits });
    expect(near.position.distanceTo(near.target)).toBeCloseTo(0.06, 10);
    const far = zoomTowardPoint({ position, target, ray, hit: null, factor: 1e6, ...limits });
    expect(far.position.distanceTo(far.target)).toBeCloseTo(30, 10);
    const again = zoomTowardPoint({ position: near.position, target: near.target, ray, hit: null, factor: 0.5, ...limits });
    expect(again.position.distanceTo(near.position)).toBeLessThan(1e-12);
  });

  it('does not mutate its inputs and survives bad factors', () => {
    const p = position.clone();
    zoomTowardPoint({ position: p, target, ray, hit: v(1, 1, 1), factor: 0.5, ...limits });
    expect(p.equals(position)).toBe(true);
    expect(zoomTowardPoint({ position, target, ray, hit: null, factor: NaN, ...limits }).position.equals(position)).toBe(true);
    expect(zoomTowardPoint({ position, target, ray, hit: null, factor: -1, ...limits }).position.equals(position)).toBe(true);
  });
});
