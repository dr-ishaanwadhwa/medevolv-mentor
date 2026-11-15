export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const ramp = (x: number, a: number, b: number) => clamp((x - a) / (b - a));
export const smooth = (x: number, a: number, b: number) => {
  const t = ramp(x, a, b);
  return t * t * (3 - 2 * t);
};
export const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
export const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
export const easeIn = (t: number) => t * t * t;
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
/** Piecewise value with smoothstep between keys [[s, v], ...]. */
export function kf(s: number, keys: [number, number][]): number {
  if (s <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    if (s <= keys[i][0]) return lerp(keys[i - 1][1], keys[i][1], smooth(s, keys[i - 1][0], keys[i][0]));
  }
  return keys[keys.length - 1][1];
}
