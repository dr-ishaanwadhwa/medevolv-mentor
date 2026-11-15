import { forwardRef, type ButtonHTMLAttributes } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/cn';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

const base =
  'inline-flex select-none items-center justify-center gap-2 rounded-xl font-medium transition-colors disabled:pointer-events-none disabled:opacity-50';
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
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'secondary', size = 'md', className, type = 'button', ...rest },
  ref,
) {
  return <button ref={ref} type={type} className={buttonClass(variant, size, className)} {...rest} />;
});

/** next/link styled like a Button. */
export function LinkButton({
  href,
  variant = 'secondary',
  size = 'md',
  className,
  children,
  ...rest
}: { href: string; variant?: Variant; size?: Size; className?: string; children: React.ReactNode } & Omit<
  React.ComponentProps<typeof Link>,
  'href' | 'className'
>) {
  return (
    <Link href={href} className={buttonClass(variant, size, className)} {...rest}>
      {children}
    </Link>
  );
}
