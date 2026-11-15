import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export type Tone = 'good' | 'warn' | 'bad' | 'info' | 'neutral';

const tones: Record<Tone, string> = {
  good: 'bg-good-soft text-good',
  warn: 'bg-warn-soft text-warn',
  bad: 'bg-bad-soft text-bad',
  info: 'bg-accent-soft text-accent',
  neutral: 'bg-surface2 text-muted',
};

export function StatusPill({ tone = 'info', children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 font-mono text-[0.74rem] font-medium',
        tones[tone],
        className,
      )}
    >
      <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-current" />
      {children}
    </span>
  );
}

/** Maps the backend `status` string to a label + tone. Unknown statuses stay neutral and honest. */
export function statusMeta(status: string): { label: string; tone: Tone; declined: boolean } {
  switch (status) {
    case 'answered':
      return { label: 'Grounded answer', tone: 'good', declined: false };
    case 'not_in_sources':
      return { label: 'Not in the textbooks', tone: 'warn', declined: true };
    case 'insufficient':
      return { label: "The books don't settle this", tone: 'warn', declined: true };
    case 'personal_refusal':
      return { label: 'Personal advice: declined', tone: 'bad', declined: true };
    default:
      return { label: status.replace(/_/g, ' '), tone: 'neutral', declined: false };
  }
}
