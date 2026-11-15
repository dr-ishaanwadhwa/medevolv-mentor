import { cn } from '@/lib/cn';

/** Shared page frame for /credits, /privacy and /terms. */
export function LegalPage({
  eyebrow,
  title,
  lead,
  children,
}: {
  eyebrow: string;
  title: string;
  lead: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="page py-8 md:py-12">
      <div className="label-mono !text-accent">{eyebrow}</div>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">{title}</h1>
      <p className="mt-3 max-w-[60ch] text-muted">{lead}</p>
      <div className="mt-8 space-y-8">{children}</div>
    </div>
  );
}

export function LegalSection({
  id,
  title,
  children,
  className,
}: {
  id?: string;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section id={id} aria-labelledby={id ? `${id}-h` : undefined} className={cn('space-y-3', className)}>
      <h2 id={id ? `${id}-h` : undefined} className="text-lg font-semibold">
        {title}
      </h2>
      <div className="space-y-3 text-[0.95rem] leading-relaxed text-ink/90">{children}</div>
    </section>
  );
}

export function ExtLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-accent underline underline-offset-2 hover:opacity-80"
    >
      {children}
    </a>
  );
}

export function BulletList({ children }: { children: React.ReactNode }) {
  return <ul className="list-disc space-y-2 pl-5 marker:text-muted">{children}</ul>;
}
