export function LogoMark({ className = 'h-8 w-8' }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <rect width="32" height="32" rx="9" fill="rgb(var(--c-accent))" />
      {/* open book with a cross: textbook + clinical */}
      <path d="M7 10.5c3-1.4 6-1.2 9 .8 3-2 6-2.2 9-.8v12c-3-1.2-6-1-9 .9-3-1.900-6-2.100-9-.9z" fill="none" stroke="rgb(var(--c-accent-ink))" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M16 11.300v12" stroke="rgb(var(--c-accent-ink))" strokeWidth="1.6" />
      <path d="M20.500 14v3.500M18.750 15.750h3.500" stroke="rgb(var(--c-accent-ink))" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      <span className="leading-tight">
        <span className="block text-[1.05rem] font-semibold tracking-tight">MedEvolv</span>
        <span className="label-mono block !text-[0.62rem] !text-accent">Mentor</span>
      </span>
    </span>
  );
}
