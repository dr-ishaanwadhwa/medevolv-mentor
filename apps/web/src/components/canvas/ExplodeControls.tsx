'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Pause, Play } from 'lucide-react';
import { Button, Tooltip } from '@/components/ui';
import { ATLAS_TIPS } from '@/lib/tips/atlas';
import {
  SYSTEM_SEPARATION_END,
  explodePlaybackAt,
  explodeStageText,
  nextExplodeStop,
  planExplodePlayback,
} from '@/lib/atlas-explode';

const reducedMotion = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
const near = (a: number, b: number) => Math.abs(a - b) < 0.005;

/**
 * Explode panel: a slider, three stage buttons and Play / Pause. Playback runs the stages with a short hold between
 * them; with prefers-reduced-motion it steps from stage to stage with no animation instead.
 */
export function ExplodeControls({ amount, familyCount, onChange }: { amount: number; familyCount: number; onChange: (n: number) => void }) {
  const [playing, setPlaying] = useState(false);
  const raf = useRef(0);
  const emitted = useRef(amount);
  const stage = explodeStageText(amount, familyCount);

  const emit = useCallback(
    (n: number) => {
      emitted.current = n;
      onChange(n);
    },
    [onChange],
  );
  const stop = useCallback(() => {
    cancelAnimationFrame(raf.current);
    setPlaying(false);
  }, []);

  // Anything other than our own playback moving the amount (the slider, Reset view, Undo) stops playback.
  useEffect(() => {
    if (playing && Math.abs(amount - emitted.current) > 1e-6) stop();
  }, [amount, playing, stop]);
  useEffect(() => () => cancelAnimationFrame(raf.current), []);

  const play = () => {
    if (reducedMotion()) {
      emit(amount >= 1 ? 0 : nextExplodeStop(amount, familyCount));
      return;
    }
    const plan = planExplodePlayback(amount, familyCount);
    const t0 = performance.now();
    setPlaying(true);
    const tick = (now: number) => {
      const { amount: a, done } = explodePlaybackAt(plan, now - t0);
      emit(a);
      if (done) setPlaying(false);
      else raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
  };

  const set = (n: number) => {
    stop();
    emit(n);
  };
  const stageButton = (label: string, value: number, tipId: 'atlas.explode.assembled' | 'atlas.explode.systems' | 'atlas.explode.pieces') => (
    <Button
      size="md"
      variant={near(amount, value) ? 'primary' : 'secondary'}
      aria-pressed={near(amount, value)}
      onClick={() => set(value)}
      tip={ATLAS_TIPS[tipId]}
      className="px-3 text-sm md:min-h-[32px]"
    >
      {label}
    </Button>
  );

  return (
    <div className="pointer-events-auto card space-y-2.5 p-3">
      <div className="flex items-center justify-between">
        <span className="label-mono">Explode</span>
        <span className="text-xs text-muted" role="status" aria-live="polite">
          {stage}
        </span>
      </div>
      <Tooltip tip={ATLAS_TIPS['atlas.explode.slider']}>
        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={Math.round(amount * 100)}
          onChange={(e) => set(Number(e.target.value) / 100)}
          aria-label="Explode amount"
          aria-valuetext={stage}
          className="h-11 w-full cursor-pointer accent-accent md:h-6"
        />
      </Tooltip>
      <div className="flex flex-wrap items-center gap-2">
        {stageButton('Assembled', 0, 'atlas.explode.assembled')}
        {familyCount >= 2 && stageButton('Systems', SYSTEM_SEPARATION_END, 'atlas.explode.systems')}
        {stageButton('Pieces', 1, 'atlas.explode.pieces')}
        <Button
          size="md"
          variant="secondary"
          onClick={playing ? stop : play}
          tip={playing ? ATLAS_TIPS['atlas.explode.pause'] : ATLAS_TIPS['atlas.explode.play']}
          className="px-3 text-sm md:min-h-[32px]"
        >
          {playing ? <Pause className="h-4 w-4" aria-hidden /> : <Play className="h-4 w-4" aria-hidden />}
          {playing ? 'Pause' : 'Play'}
        </Button>
      </div>
    </div>
  );
}
