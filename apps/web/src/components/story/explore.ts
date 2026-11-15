/** Pure helpers for the "Try your own question" chapter (no three.js, so they can be checked in plain node). */

export type Vec3 = [number, number, number];

/**
 * Similarity-weighted mean of points. Negative weights count as zero; if every weight is zero
 * the plain mean is used. Returns null for an empty list.
 */
export function weightedMean(points: readonly Vec3[], weights: readonly number[]): Vec3 | null {
  if (!points.length) return null;
  let sw = 0;
  const m: Vec3 = [0, 0, 0];
  points.forEach((p, k) => {
    const w = Math.max(0, weights[k] ?? 0);
    sw += w;
    m[0] += p[0] * w; m[1] += p[1] * w; m[2] += p[2] * w;
  });
  if (sw > 1e-12) return [m[0] / sw, m[1] / sw, m[2] / sw];
  const n = points.length;
  return [0, 1, 2].map((a) => points.reduce((s, p) => s + p[a], 0) / n) as Vec3;
}
