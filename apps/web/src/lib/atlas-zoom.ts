import * as T from 'three';

/**
 * Cursor-centred zoom for the atlas camera. Pure maths so Node tests can import it.
 * Idea adapted from human-atlas-enhanced (MIT, see apps/web/THIRD_PARTY_NOTICES.md): zoom towards the point under the
 * cursor or pinch centre instead of towards the orbit target.
 *
 * Scaling the camera and its orbit target about an anchor keeps the anchor at the same screen position, so the
 * structure under the cursor stays under the cursor while everything else grows or shrinks around it.
 */
export interface ZoomInput {
  position: T.Vector3;
  target: T.Vector3;
  /** The ray through the cursor (world space). Used for the fallback anchor when nothing is under the cursor. */
  ray: T.Ray;
  /** First visible surface under the cursor, or null when the cursor is over empty space. */
  hit: T.Vector3 | null;
  /** New distance divided by old distance: below 1 zooms in, above 1 zooms out. */
  factor: number;
  minDistance: number;
  maxDistance: number;
}

export interface ZoomResult {
  position: T.Vector3;
  target: T.Vector3;
}

/** Largest zoom step from one wheel tick or pinch update, so a fast flick cannot jump across the body. */
const MAX_STEP = 1.6;

/**
 * Convert one wheel event to a distance factor. Touchpad pinch arrives as ctrl+wheel with small deltas, so it gets a
 * larger gain. `deltaMode` 1 is lines and 2 is pages (Firefox mouse wheels).
 */
export function wheelZoomFactor(deltaY: number, deltaMode = 0, ctrlKey = false): number {
  if (!Number.isFinite(deltaY) || deltaY === 0) return 1;
  const px = deltaMode === 1 ? deltaY * 16 : deltaMode === 2 ? deltaY * 400 : deltaY;
  const f = Math.exp(px * (ctrlKey ? 0.01 : 0.0016));
  return Math.min(MAX_STEP, Math.max(1 / MAX_STEP, f));
}

/** Pinch: fingers moving apart (distance grows) zoom in, so the camera distance shrinks by the same ratio. */
export function pinchZoomFactor(previousSpan: number, currentSpan: number): number {
  if (!(previousSpan > 0) || !(currentSpan > 0)) return 1;
  return Math.min(MAX_STEP, Math.max(1 / MAX_STEP, previousSpan / currentSpan));
}

/** Where to zoom towards: the surface under the cursor, else the cursor ray's crossing of the plane through the target. */
export function zoomAnchor(position: T.Vector3, target: T.Vector3, ray: T.Ray, hit: T.Vector3 | null): T.Vector3 {
  if (hit) return hit.clone();
  const normal = target.clone().sub(position);
  if (normal.lengthSq() < 1e-12) return target.clone();
  const plane = new T.Plane().setFromNormalAndCoplanarPoint(normal.normalize(), target);
  return ray.intersectPlane(plane, new T.Vector3()) ?? target.clone();
}

/** Scale camera and target about the anchor. The camera distance stays inside [minDistance, maxDistance]. */
export function zoomTowardPoint(input: ZoomInput): ZoomResult {
  const { position, target, factor, minDistance, maxDistance } = input;
  const dist = position.distanceTo(target);
  if (!(dist > 0) || !Number.isFinite(factor) || factor <= 0) return { position: position.clone(), target: target.clone() };
  const wanted = Math.min(maxDistance, Math.max(minDistance, dist * factor));
  // Never push past a limit the camera is already beyond: only allow movement back inside the range.
  const bounded = dist < minDistance ? Math.max(dist, Math.min(wanted, maxDistance)) : dist > maxDistance ? Math.min(dist, Math.max(wanted, minDistance)) : wanted;
  const s = bounded / dist;
  if (Math.abs(s - 1) < 1e-9) return { position: position.clone(), target: target.clone() };
  const anchor = zoomAnchor(position, target, input.ray, input.hit);
  return {
    position: anchor.clone().add(position.clone().sub(anchor).multiplyScalar(s)),
    target: anchor.clone().add(target.clone().sub(anchor).multiplyScalar(s)),
  };
}
