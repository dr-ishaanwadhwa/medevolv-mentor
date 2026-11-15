'use client';

import { cn } from '@/lib/cn';
import type { TipProp } from '@/lib/tips';
import { useTip } from './Tooltip';

/**
 * Numbered source marker. Same look as the inline [n] chips inside <Markdown>.
 * Pass `tip` with the real pointer (for example "Harrison 22e, ch N, p N. Opens the source.");
 * without it the tip is the generic "Source n. Opens the source."
 */
export function CitationChip({
  n,
  onClick,
  cited = true,
  className,
  tip,
}: {
  n: number;
  onClick?: (n: number) => void;
  cited?: boolean;
  className?: string;
  tip?: TipProp;
}) {
  const t = useTip(tip ?? { purpose: `Source ${n} for this answer.`, effect: 'Opens the source.' }, { longPress: true });
  return (
    <>
      <button
        type="button"
        {...t.bind({})}
        ref={t.ref}
        onClick={() => onClick?.(n)}
        aria-label={`Open source ${n}`}
        className={cn('cite-chip', !cited && 'uncited', className)}
      >
        {n}
      </button>
      {t.node}
    </>
  );
}
