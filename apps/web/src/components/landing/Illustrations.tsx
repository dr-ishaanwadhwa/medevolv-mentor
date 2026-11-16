import { BOOK_COLORS } from '../story/palette';
import { BOOKS } from './facts';

/** Static fallback art (no WebGL, Save-Data, slow connection or after the 6 s time fallback). Inline SVG, a few KB,
 * themed by Tailwind's dark variant. Shown only when the stage sets data-landing="static" (see landing.css rules in
 * LandingStage) or JavaScript is off. Decorative: every claim it shows is also in the text beside it. */

const SPOTS: [number, number][] = [[62, 52], [150, 38], [236, 62], [96, 118], [190, 112], [278, 120], [160, 168]];

function cloud(seed: number, cx: number, cy: number, n: number): [number, number][] {
  const pts: [number, number][] = [];
  let s = seed * 9301 + 49297;
  for (let i = 0; i < n; i++) {
    s = (s * 9301 + 49297) % 233280;
    const a = (s / 233280) * Math.PI * 2;
    s = (s * 9301 + 49297) % 233280;
    const r = Math.sqrt(s / 233280) * 26;
    pts.push([cx + Math.cos(a) * r * 1.25, cy + Math.sin(a) * r * 0.85]);
  }
  return pts;
}

export function LibraryIllustration({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 320 210" role="img" aria-label="Seven clusters of dots, one per textbook in the library" className={className}>
      {(['light', 'dark'] as const).map((mode) => (
        <g key={mode} className={mode === 'light' ? 'dark:hidden' : 'hidden dark:inline'}>
          {BOOKS.map((b, i) => {
            const col = BOOK_COLORS[b.id]?.[mode] ?? '#888';
            return cloud(i + 1, SPOTS[i][0], SPOTS[i][1], 46).map(([x, y], k) => (
              <circle key={`${b.id}${k}`} cx={x.toFixed(1)} cy={y.toFixed(1)} r={k % 5 === 0 ? 1.9 : 1.3} fill={col} opacity={0.8} />
            ));
          })}
        </g>
      ))}
    </svg>
  );
}

export function ChiasmIllustration({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 320 200" role="img" aria-label="Schematic of the optic chiasm: two optic nerves meet and cross, then continue as two optic tracts" className={className}>
      <g fill="none" strokeLinecap="round" className="stroke-accent" strokeWidth="9" opacity="0.85">
        <path d="M60 30 C 110 70, 140 80, 160 100" />
        <path d="M260 30 C 210 70, 180 80, 160 100" />
        <path d="M160 100 C 140 120, 110 140, 70 175" />
        <path d="M160 100 C 180 120, 210 140, 250 175" />
      </g>
      <g fill="none" strokeLinecap="round" className="stroke-ink" strokeWidth="1.2" opacity="0.5">
        <path d="M60 30 C 110 70, 140 80, 160 100" />
        <path d="M260 30 C 210 70, 180 80, 160 100" />
        <path d="M160 100 C 140 120, 110 140, 70 175" />
        <path d="M160 100 C 180 120, 210 140, 250 175" />
      </g>
      <g className="fill-muted" fontFamily="var(--font-mono), monospace" fontSize="9">
        <text x="30" y="20">optic nerves</text>
        <text x="200" y="192">optic tracts</text>
        <text x="172" y="96">chiasm</text>
      </g>
    </svg>
  );
}

export function FlowIllustration({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 320 120" role="img" aria-label="A small flowchart of boxes joined by arrows" className={className}>
      <g className="fill-surface2 stroke-border" strokeWidth="1.2">
        <rect x="8" y="44" width="76" height="32" rx="8" />
        <rect x="122" y="10" width="76" height="32" rx="8" />
        <rect x="122" y="78" width="76" height="32" rx="8" />
        <rect x="236" y="44" width="76" height="32" rx="8" />
      </g>
      <g fill="none" className="stroke-accent" strokeWidth="1.6">
        <path d="M84 60 C 104 60, 104 26, 122 26" />
        <path d="M84 60 C 104 60, 104 94, 122 94" />
        <path d="M198 26 C 218 26, 218 60, 236 60" />
        <path d="M198 94 C 218 94, 218 60, 236 60" />
      </g>
    </svg>
  );
}
