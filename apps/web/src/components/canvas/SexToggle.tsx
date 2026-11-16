'use client';

import { useRef, type KeyboardEvent, type Ref } from 'react';
import { cn } from '@/lib/cn';
import { Tooltip } from '@/components/ui/Tooltip';
import { ATLAS_TIPS } from '@/lib/tips/atlas';
import { FEMALE_NOTE, SEXES, type Sex } from '@/lib/atlas-sex';

const LABEL: Record<Sex, string> = { male: 'Male', female: 'Female (organs)' };
const TIP = { male: ATLAS_TIPS['atlas.sex.male'], female: ATLAS_TIPS['atlas.sex.female'] } as const;

/**
 * "Male | Female (organs)" segmented control (PRD 4.5, F-10). Rendered only when the `female_atlas` flag is on.
 * radiogroup with two radios, one tab stop (roving tabindex), arrows move and select, Space/Enter select.
 */
export function SexToggle({
  value,
  onChange,
  femaleRef,
  describedBy,
}: {
  value: Sex;
  onChange: (next: Sex) => void;
  /** lets the confirm sheet return focus to the Female radio */
  femaleRef?: Ref<HTMLButtonElement>;
  describedBy?: string;
}) {
  const refs = useRef<Record<Sex, HTMLButtonElement | null>>({ male: null, female: null });

  const move = (e: KeyboardEvent, from: Sex) => {
    let to: Sex | null = null;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') to = from === 'male' ? 'female' : 'male';
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') to = from === 'female' ? 'male' : 'female';
    if (!to) return;
    e.preventDefault();
    refs.current[to]?.focus();
    if (to !== value) onChange(to);
  };

  return (
    <div
      role="radiogroup"
      aria-label="Body model"
      aria-describedby={describedBy}
      className="inline-flex rounded-xl border border-border bg-surface p-0.5 shadow-card"
    >
      {SEXES.map((s) => {
        const checked = s === value;
        return (
          <Tooltip key={s} tip={TIP[s]}>
            <button
              type="button"
              role="radio"
              aria-checked={checked}
              tabIndex={checked ? 0 : -1}
              ref={(el) => {
                refs.current[s] = el;
                if (s === 'female' && femaleRef) {
                  if (typeof femaleRef === 'function') femaleRef(el);
                  else (femaleRef as { current: HTMLButtonElement | null }).current = el;
                }
              }}
              onClick={() => {
                if (!checked) onChange(s);
              }}
              onKeyDown={(e) => {
                if (e.key === ' ' || e.key === 'Enter') {
                  e.preventDefault();
                  if (!checked) onChange(s);
                } else move(e, s);
              }}
              className={cn(
                'min-h-[44px] rounded-[10px] px-3 text-sm font-medium transition-colors',
                checked ? 'bg-accent text-accent-ink' : 'text-muted hover:bg-surface2 hover:text-ink',
              )}
            >
              {LABEL[s]}
            </button>
          </Tooltip>
        );
      })}
    </div>
  );
}

/** The honest note shown under the toggle while the female model is active. */
export function FemaleNote({ id }: { id: string }) {
  return (
    <p id={id} className="max-w-[340px] rounded-lg border border-border bg-surface/95 px-2.5 py-1.5 text-[0.78rem] leading-snug text-muted shadow-card backdrop-blur">
      {FEMALE_NOTE}
    </p>
  );
}
