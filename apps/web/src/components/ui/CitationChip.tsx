import { cn } from '@/lib/cn';

/** Numbered source marker. Same look as the inline [n] chips inside <Markdown>. */
export function CitationChip({
  n,
  onClick,
  cited = true,
  className,
}: {
  n: number;
  onClick?: (n: number) => void;
  cited?: boolean;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onClick?.(n)}
      aria-label={`Open source ${n}`}
      className={cn('cite-chip', !cited && 'uncited', className)}
    >
      {n}
    </button>
  );
}
