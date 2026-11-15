'use client';

import { forwardRef, type ButtonHTMLAttributes } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/cn';
import { resolveTip, type TipProp } from '@/lib/tips';
import { mergeRefs, useTip } from './Tooltip';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

const base =
  'inline-flex select-none items-center justify-center gap-2 rounded-xl font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 aria-disabled:cursor-not-allowed aria-disabled:opacity-50';
const variants: Record<Variant, string> = {
  primary: 'bg-accent text-accent-ink hover:bg-accent/90 active:bg-accent/80',
  secondary: 'border border-border bg-surface text-ink hover:bg-surface2',
  ghost: 'text-muted hover:bg-surface2 hover:text-ink',
  danger: 'bg-bad-soft text-bad hover:bg-bad-soft/70',
};
// md is 44px tall so every default button is a valid touch target.
const sizes: Record<Size, string> = {
  sm: 'min-h-[36px] px-3 text-sm md:min-h-[32px]',
  md: 'min-h-[44px] px-4 text-[0.95rem]',
  lg: 'min-h-[48px] px-5 text-base',
};

export function buttonClass(variant: Variant = 'secondary', size: Size = 'md', extra?: string) {
  return cn(base, variants[variant], sizes[size], extra);
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  /** What this control is for and what it does: a registry id or a plain {purpose, effect, disabled?}. */
  tip?: TipProp;
  /** Icon-only buttons get touch long-press to show the tip. Never set it for text buttons or links. */
  iconOnly?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'secondary', size = 'md', className, type = 'button', tip, iconOnly, disabled, onClick, ...rest },
  ref,
) {
  const t = useTip(tip, { longPress: iconOnly, disabled });
  // With a disabled reason the button stays focusable and hoverable (aria-disabled) so the reason can be read.
  const soft = !!disabled && !!resolveTip(tip)?.disabled;
  return (
    <>
      <button
        type={type}
        className={buttonClass(variant, size, className)}
        {...t.bind(rest)}
        ref={mergeRefs(ref, t.ref)}
        disabled={soft ? undefined : disabled}
        aria-disabled={soft ? true : undefined}
        // A submit button must not submit while it only looks disabled.
        onClick={soft ? (e) => e.preventDefault() : onClick}
      />
      {t.node}
    </>
  );
});

/** next/link styled like a Button. Links never get long-press handling. */
export function LinkButton({
  href,
  variant = 'secondary',
  size = 'md',
  className,
  children,
  tip,
  ...rest
}: { href: string; variant?: Variant; size?: Size; className?: string; children: React.ReactNode; tip?: TipProp } & Omit<
  React.ComponentProps<typeof Link>,
  'href' | 'className'
>) {
  const t = useTip(tip);
  return (
    <>
      <Link href={href} className={buttonClass(variant, size, className)} {...t.bind(rest)} ref={t.ref}>
        {children}
      </Link>
      {t.node}
    </>
  );
}
