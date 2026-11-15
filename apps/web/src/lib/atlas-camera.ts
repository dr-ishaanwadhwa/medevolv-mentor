import * as T from 'three';

/** Pure camera maths for the atlas (the `frame3` goal pose), kept free of scene objects so Node tests can import it. */
export interface Inset {
  right?: number;
  bottom?: number;
}

export interface GoalPose {
  target: T.Vector3;
  position: T.Vector3;
  /** distance from target to camera, used for the controls' max distance */
  dist: number;
}

export interface GoalView {
  /** viewport size in CSS px */
  width: number;
  height: number;
  aspect: number;
  /** vertical field of view in degrees */
  fov: number;
}

/**
 * Goal pose for framing `boxes`.
 * `whole` frames the whole visible body (default direction, wider margin); otherwise it frames a selection.
 * `dir` is the view direction from target to camera; when omitted the default direction for the mode is used.
 * Returns null when there is nothing to frame.
 */
export function computeGoalPose(
  boxes: readonly T.Box3[],
  whole: boolean,
  inset: Inset | undefined,
  view: GoalView,
  dir?: T.Vector3,
): GoalPose | null {
  const box = new T.Box3();
  for (const b of boxes) box.union(b);
  if (box.isEmpty()) return null;
  const size = box.getSize(new T.Vector3());
  const center = box.getCenter(new T.Vector3());
  const tanHalf = Math.tan(T.MathUtils.degToRad(view.fov / 2));
  const aspect = Math.max(0.3, view.aspect);
  const W = view.width || 1;
  const H = view.height || 1;
  const freeW = Math.max(0.35, (W - (inset?.right ?? 0)) / W);
  const freeH = Math.max(0.35, (H - (inset?.bottom ?? 0)) / H);
  const fitH = size.y / (2 * tanHalf) / freeH;
  const fitW = size.x / (2 * tanHalf * aspect) / freeW;
  let dist = Math.max(fitH, fitW, size.z * 0.9) * (whole ? 1.18 : 2.1) + size.z / 2;
  dist = Math.max(dist, whole ? 1 : 0.09);
  const d = (dir ?? new T.Vector3(whole ? 0.32 : 0.25, 0.08, 1)).clone().normalize();
  return { target: center, position: center.clone().addScaledVector(d, dist), dist };
}
