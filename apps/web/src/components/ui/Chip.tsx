'use client';

import type { ButtonHTMLAttributes, ReactNode } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/cn';
import type { TipProp } from '@/lib/tips';
import { useTip } from './Tooltip';

const chip =
  'inline-flex min-h-[44px] items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 text-sm text-ink transition-colors hover:border-accent/50 hover:bg-accent-soft md:min-h-[34px]';

/** Pill-shaped action/link. Pass `href` for a link, otherwise it is a button. */
export function Chip({
  href,
  children,
  className,
  tip,
  ...rest
}: { href?: string; children: ReactNode; className?: string; tip?: TipProp } & ButtonHTMLAttributes<HTMLButtonElement>) {
  const t = useTip(tip);
  if (href) {
    // ARIA and data props now reach the link (they used to be dropped).
    return (
      <>
        <Link href={href} className={cn(chip, className)} {...(t.bind(rest) as object)} ref={t.ref}>
          {children}
        </Link>
        {t.node}
      </>
    );
  }
  return (
    <>
      <button type="button" className={cn(chip, className)} {...t.bind(rest)} ref={t.ref}>
        {children}
      </button>
      {t.node}
    </>
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
