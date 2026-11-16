import type { Part, SystemId } from './anatomy';

/**
 * Staged "explode" view. Pure layout and timing maths, no three.js, so Node tests can import it.
 * Adapted from human-atlas-enhanced (MIT, see apps/web/THIRD_PARTY_NOTICES.md): stage 1 slides whole system families
 * sideways into their own lanes, stage 2 spreads every structure into its own cell. Our version keys by part id (we
 * have no identity layer) and runs on both the male and the female model.
 */

/** Presentation families only. They group systems for the view and make no anatomical claim. */
export type ExplodeFamily = 'support' | 'muscular' | 'visceral' | 'vascular' | 'neural-sensory' | 'surface';
export const EXPLODE_FAMILY_ORDER: readonly ExplodeFamily[] = ['support', 'muscular', 'visceral', 'vascular', 'neural-sensory', 'surface'];
export const EXPLODE_FAMILY_BY_SYSTEM: Record<SystemId, ExplodeFamily> = {
  skeletal: 'support',
  connective: 'support',
  muscular: 'muscular',
  cardiac: 'visceral',
  respiratory: 'visceral',
  digestive: 'visceral',
  urinary: 'visceral',
  endocrine: 'visceral',
  reproductive: 'visceral',
  reproductive_female: 'visceral',
  lymphatic: 'visceral',
  pregnancy: 'visceral',
  arterial: 'vascular',
  venous: 'vascular',
  nervous: 'neural-sensory',
  sensory: 'neural-sensory',
  integumentary: 'surface',
};

/** Explode amount at which the families have finished separating (stage 1 ends, stage 2 begins). */
export const SYSTEM_SEPARATION_END = 0.3;

export type Vec3 = [number, number, number];
export type Bounds3 = [Vec3, Vec3];
type LayoutPart = Pick<Part, 'id' | 'system' | 'bounds'>;

export interface LayoutCell {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ExplodeTarget {
  family: ExplodeFamily;
  /** offset applied during stage 1 (sideways, whole family) */
  familyTranslation: Vec3;
  /** offset applied during stage 2 (into this part's cell) */
  pieceTranslation: Vec3;
  bounds: Bounds3;
}

export interface ExplodeLayout {
  /** part id to target */
  targets: ReadonlyMap<string, ExplodeTarget>;
  /** how many families the layout separates (stage 1 needs two or more) */
  familyCount: number;
}

const byId = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
const smoothstep = (t: number) => t * t * (3 - 2 * t);
const clamp01 = (n: number) => (Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : 0);

function safeBounds(part: LayoutPart): Bounds3 {
  const side = (s: 0 | 1) =>
    [0, 1, 2].map((axis) => {
      const a = part.bounds?.[0]?.[axis];
      const b = part.bounds?.[1]?.[axis];
      return Number.isFinite(a) && Number.isFinite(b) ? (s ? Math.max(a, b) : Math.min(a, b)) : 0;
    }) as Vec3;
  return [side(0), side(1)];
}

function union(boxes: Bounds3[]): Bounds3 {
  if (!boxes.length) return [[0, 0, 0], [0, 0, 0]];
  const pick = (s: 0 | 1) =>
    [0, 1, 2].map((a) => boxes.reduce((n, b) => (s ? Math.max(n, b[1][a]) : Math.min(n, b[0][a])), s ? -Infinity : Infinity)) as Vec3;
  return [pick(0), pick(1)];
}

const centerOf = (b: Bounds3): Vec3 => [0, 1, 2].map((a) => (b[0][a] + b[1][a]) / 2) as Vec3;
const widthOf = (b: Bounds3) => Math.max(0.001, b[1][0] - b[0][0]);

/** Shelf-pack one cell per part, centred on the origin. Wider rows first, tallest parts first. */
export function packCells(parts: readonly LayoutPart[], aspect = 1): { cells: Map<string, LayoutCell>; width: number; height: number } {
  const cards = parts.map((p) => {
    const b = safeBounds(p);
    return {
      id: p.id,
      width: Math.max(0.035, b[1][0] - b[0][0]) + 0.04,
      height: Math.max(0.035, b[1][1] - b[0][1]) + 0.04,
    };
  });
  const area = cards.reduce((n, c) => n + c.width * c.height, 0);
  const maxWidth = Math.max(0.3, ...cards.map((c) => c.width));
  const targetWidth = Math.max(maxWidth, Math.sqrt(area * Math.max(0.5, Math.min(1.5, aspect))) * 1.18);
  cards.sort((a, b) => b.height - a.height || byId(a.id, b.id));
  const cells = new Map<string, LayoutCell>();
  let x = 0;
  let y = 0;
  let row = 0;
  let usedWidth = 0;
  for (const c of cards) {
    if (x > 0 && x + c.width > targetWidth) {
      x = 0;
      y += row;
      row = 0;
    }
    cells.set(c.id, { x: x + c.width / 2, y: -y - c.height / 2, width: c.width, height: c.height });
    x += c.width;
    usedWidth = Math.max(usedWidth, x);
    row = Math.max(row, c.height);
  }
  const height = y + row;
  cells.forEach((c) => {
    c.x -= usedWidth / 2;
    c.y += height / 2;
  });
  return { cells, width: usedWidth, height };
}

/**
 * Stable layout for a set of parts. The inputs are only the parts themselves, so toggling layers, hiding or
 * isolating never moves a piece that is already pulled apart.
 */
export function createExplodeLayout(parts: readonly LayoutPart[]): ExplodeLayout {
  const ordered = [...parts].sort((a, b) => byId(a.id, b.id));
  const assembled = union(ordered.map(safeBounds));
  const center = centerOf(assembled);
  const families = EXPLODE_FAMILY_ORDER.filter((f) => ordered.some((p) => EXPLODE_FAMILY_BY_SYSTEM[p.system] === f));
  const groups = families.map((family) => {
    const members = ordered.filter((p) => EXPLODE_FAMILY_BY_SYSTEM[p.system] === family);
    const bounds = union(members.map(safeBounds));
    const packed = packCells(members, 0.65);
    return { family, members, bounds, packed, midWidth: widthOf(bounds), finalWidth: Math.max(widthOf(bounds), packed.width) };
  });
  const span = Math.max(...assembled[1].map((n, a) => n - assembled[0][a]), 0.001);
  const gap = span * 0.07;
  const gaps = gap * Math.max(0, groups.length - 1);
  const midTotal = groups.reduce((n, g) => n + g.midWidth, 0) + gaps;
  const finalTotal = groups.reduce((n, g) => n + g.finalWidth, 0) + gaps;
  let midX = center[0] - midTotal / 2;
  let finalX = center[0] - finalTotal / 2;
  const targets = new Map<string, ExplodeTarget>();
  for (const g of groups) {
    const midCenter = midX + g.midWidth / 2;
    const finalCenter = finalX + g.finalWidth / 2;
    // A lone family stays exactly where it is assembled.
    const translation = groups.length < 2 ? 0 : midCenter - centerOf(g.bounds)[0];
    for (const p of g.members) {
      const bounds = safeBounds(p);
      const c = centerOf(bounds);
      const cell = g.packed.cells.get(p.id)!;
      const pieceTranslation: Vec3 =
        ordered.length === 1 ? [0, 0, 0] : [cell.x + finalCenter - c[0] - translation, cell.y + center[1] - c[1], center[2] - c[2]];
      targets.set(p.id, { family: g.family, familyTranslation: [translation, 0, 0], pieceTranslation, bounds });
    }
    midX += g.midWidth + gap;
    finalX += g.finalWidth + gap;
  }
  return { targets, familyCount: groups.length };
}

/** Stage progress for an amount in [0, 1]: families move first (to 0.3), then pieces. One family skips stage 1. */
export function explodeProgress(amount: number, familyCount: number): { family: number; piece: number } {
  const t = clamp01(amount);
  if (familyCount < 2) return { family: 0, piece: smoothstep(t) };
  return {
    family: smoothstep(Math.min(1, t / SYSTEM_SEPARATION_END)),
    piece: smoothstep(Math.max(0, (t - SYSTEM_SEPARATION_END) / (1 - SYSTEM_SEPARATION_END))),
  };
}

/** The world-space offset for one part at `amount`. Zero at 0, so an assembled body is untouched. */
export function explodeOffset(target: ExplodeTarget, amount: number, familyCount: number): Vec3 {
  if (clamp01(amount) === 0) return [0, 0, 0];
  const p = explodeProgress(amount, familyCount);
  return [0, 1, 2].map((a) => target.familyTranslation[a] * p.family + target.pieceTranslation[a] * p.piece) as Vec3;
}

export function explodeStageText(amount: number, familyCount: number): string {
  const t = clamp01(amount);
  if (t === 0) return 'Assembled';
  if (t === 1) return 'Every piece apart';
  if (familyCount >= 2 && Math.abs(t - SYSTEM_SEPARATION_END) < 1e-5) return 'Systems apart';
  return familyCount >= 2 && t < SYSTEM_SEPARATION_END ? 'Separating systems' : 'Separating structures';
}

/** The stage a Play or step press moves to next: systems apart first (when there are two or more), then every piece. */
export function nextExplodeStop(amount: number, familyCount: number): number {
  return familyCount >= 2 && amount < SYSTEM_SEPARATION_END - 1e-6 ? SYSTEM_SEPARATION_END : 1;
}

// ---------------------------------------------------------------- playback

export const EXPLODE_STAGE_MS = 1500;
export const EXPLODE_HOLD_MS = 500;

export interface ExplodePlan {
  from: number;
  /** each leg: where it ends and how long it takes, then a hold before the next leg */
  legs: { to: number; ms: number }[];
}

/** Legs scale with the distance left to travel, with a short minimum so resuming mid-stage still reads as motion. */
function legMs(from: number, to: number, familyCount: number): number {
  const span = to === SYSTEM_SEPARATION_END ? SYSTEM_SEPARATION_END : familyCount >= 2 ? 1 - SYSTEM_SEPARATION_END : 1;
  return Math.max(400, EXPLODE_STAGE_MS * Math.min(1, Math.abs(to - from) / span));
}

/** Play from `amount`: through "systems apart" to "every piece". At the end, Play starts again from assembled. */
export function planExplodePlayback(amount: number, familyCount: number): ExplodePlan {
  const from = clamp01(amount) >= 1 ? 0 : clamp01(amount);
  const legs: ExplodePlan['legs'] = [];
  let at = from;
  while (at < 1 - 1e-6) {
    const to = nextExplodeStop(at, familyCount);
    legs.push({ to, ms: legMs(at, to, familyCount) });
    at = to;
  }
  return { from, legs };
}

/** Amount at `elapsed` ms into the plan, eased within each leg and holding between legs. */
export function explodePlaybackAt(plan: ExplodePlan, elapsed: number): { amount: number; done: boolean } {
  let from = plan.from;
  let t = Math.max(0, elapsed);
  for (let i = 0; i < plan.legs.length; i++) {
    const leg = plan.legs[i];
    if (t < leg.ms) return { amount: from + (leg.to - from) * smoothstep(t / leg.ms), done: false };
    t -= leg.ms;
    from = leg.to;
    const last = i === plan.legs.length - 1;
    if (last) break;
    if (t < EXPLODE_HOLD_MS) return { amount: from, done: false };
    t -= EXPLODE_HOLD_MS;
  }
  return { amount: from, done: true };
}

/** How many presentation families a model's parts fall into (stage 1 needs two or more). The skin is never loaded. */
export function explodeFamilyCount(parts: readonly Pick<Part, 'system'>[]): number {
  const seen = new Set<ExplodeFamily>();
  for (const p of parts) if (p.system !== 'integumentary') seen.add(EXPLODE_FAMILY_BY_SYSTEM[p.system]);
  return seen.size;
}
