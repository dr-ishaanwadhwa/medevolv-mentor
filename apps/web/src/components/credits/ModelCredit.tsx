import Link from 'next/link';
import { cn } from '@/lib/cn';
import { MODELS, type ModelId } from './models';

/**
 * One-line credit for the 3D model on screen, linking to /credits.
 * Place it under every view that renders a mesh (CC BY 4.0 requires attribution).
 * Pass `model` as the id of the model actually rendered, or an array when a view shows several.
 */
export function ModelCredit({
  model = 'bodyparts3d',
  className,
}: {
  model?: ModelId | ModelId[];
  className?: string;
}) {
  const ids = Array.isArray(model) ? model : [model];
  return (
    <p className={cn('text-[0.72rem] leading-snug text-muted', className)}>
      {ids.map((id, i) => (
        <span key={id}>
          {i > 0 && <span aria-hidden> · </span>}
          {MODELS[id].short}
        </span>
      ))}
      {' · '}
      <Link href="/credits" className="underline underline-offset-2 hover:text-ink">
        Credits
      </Link>
    </p>
  );
}
