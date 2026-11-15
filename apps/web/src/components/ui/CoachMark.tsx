'use client';

import { useEffect, useState, type ReactNode } from 'react';

const KEY = (id: string) => `mm-coach:${id}`;

export function coachSeen(id: string): boolean {
  try {
    return localStorage.getItem(KEY(id)) === '1';
  } catch {
    return false; // storage blocked: it shows again, which is harmless
  }
}

function markSeen(id: string) {
  try {
    localStorage.setItem(KEY(id), '1');
  } catch {
    /* ignored */
  }
}

/**
 * One-time, dismissible hint on touch devices, for the few non-obvious controls.
 * The workstream that owns the feature places it, and passes `live={false}` (or does not render it)
 * while the feature is off, so a coach mark never points at something that is not there.
 */
export function CoachMark({
  id,
  text,
  live = true,
  children,
}: {
  id: string;
  text: string;
  live?: boolean;
  children: ReactNode;
}) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (!live) return;
    const touch = window.matchMedia?.('(hover: none) and (pointer: coarse)').matches;
    if (touch && !coachSeen(id)) setShow(true);
  }, [id, live]);

  const dismiss = () => {
    markSeen(id);
    setShow(false);
  };

  return (
    <span className="relative inline-flex">
      {children}
      {live && show && (
        <span
          role="note"
          className="absolute left-0 top-full z-[70] mt-2 flex w-60 animate-fade-in items-start gap-2 rounded-xl bg-ink px-3 py-2 text-xs leading-snug text-bg shadow-pop motion-reduce:animate-none"
        >
          <span className="flex-1">{text}</span>
          <button
            type="button"
            onClick={dismiss}
            data-tip-id="shell.coach.dismiss"
            className="-my-1 -mr-1 min-h-[32px] shrink-0 rounded-md px-2 font-semibold underline underline-offset-2"
          >
            Got it
          </button>
        </span>
      )}
    </span>
  );
}
