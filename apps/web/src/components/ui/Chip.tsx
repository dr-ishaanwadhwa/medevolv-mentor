import type { ButtonHTMLAttributes, ReactNode } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/cn';

const chip =
  'inline-flex min-h-[44px] items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 text-sm text-ink transition-colors hover:border-accent/50 hover:bg-accent-soft md:min-h-[34px]';

/** Pill-shaped action/link. Pass `href` for a link, otherwise it is a button. */
export function Chip({
  href,
  children,
  className,
  ...rest
}: { href?: string; children: ReactNode; className?: string } & ButtonHTMLAttributes<HTMLButtonElement>) {
  if (href) {
    return (
      <Link href={href} className={cn(chip, className)}>
        {children}
      </Link>
    );
  }
  return (
    <button type="button" className={cn(chip, className)} {...rest}>
      {children}
    </button>
  );
}

/** Small non-interactive tag (mono label). */
export function Tag({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md bg-surface2 px-1.5 py-0.5 font-mono text-[0.68rem] font-medium uppercase tracking-wider text-muted',
        className,
      )}
    >
      {children}
    </span>
  );
}
