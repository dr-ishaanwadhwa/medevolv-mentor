'use client';

import { useEffect, useLayoutEffect, useRef, useState, type ReactNode, type RefObject } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/cn';

const GAP = 4;
const EDGE = 8;

/**
 * A small action list opened by a trigger button (a disclosure, not an ARIA menu). Rendered in a portal at fixed
 * position from the trigger's rect, so a scrolling parent (a card row with overflow-x) never clips it.
 * Focus moves to the first item on open; Escape, Tab and an outside pointerdown close it; focus returns to the trigger
 * when it was inside the list. The trigger carries aria-expanded and aria-controls={id}.
 */
export function Popover({
  id,
  anchor,
  open,
  onClose,
  label,
  className,
  children,
}: {
  id: string;
  anchor: RefObject<HTMLElement | null>;
  open: boolean;
  onClose: () => void;
  label: string;
  className?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const focusInside = useRef(false);
  // callers pass an inline onClose; a ref keeps the open effect from re-running (and re-focusing) on every render
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);

  useLayoutEffect(() => {
    if (!open) {
      setPos(null);
      return;
    }
    const place = () => {
      const a = anchor.current?.getBoundingClientRect();
      const el = ref.current;
      if (!a || !el) return;
      const w = el.offsetWidth;
      const h = el.offsetHeight;
      const left = Math.min(Math.max(EDGE, a.right - w), window.innerWidth - w - EDGE);
      const below = a.bottom + GAP;
      const top = below + h <= window.innerHeight - EDGE ? below : Math.max(EDGE, a.top - GAP - h);
      setPos({ left, top });
    };
    place();
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
    return () => {
      window.removeEventListener('resize', place);
      window.removeEventListener('scroll', place, true);
    };
  }, [open, anchor]);

  useEffect(() => {
    if (!open) return;
    const items = () => [...(ref.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href]') ?? [])];
    items()[0]?.focus();
    const back = () => anchor.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (!ref.current?.contains(document.activeElement)) return;
      const list = items();
      const i = list.indexOf(document.activeElement as HTMLElement);
      if (e.key === 'Escape') {
        e.preventDefault();
        closeRef.current();
        back();
      } else if (e.key === 'Tab') {
        e.preventDefault();
        closeRef.current();
        back();
      } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        const n = list.length;
        if (n) list[(i + (e.key === 'ArrowDown' ? 1 : n - 1) + n) % n]?.focus();
      }
    };
    const onDown = (e: PointerEvent) => {
      const t = e.target as Node;
      if (ref.current?.contains(t) || anchor.current?.contains(t)) return;
      closeRef.current();
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onDown, true);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onDown, true);
      // closed by picking an item: give focus back to the trigger instead of dropping it on <body>
      if (focusInside.current) back();
      focusInside.current = false;
    };
  }, [open, anchor]);

  if (!open || typeof document === 'undefined') return null;
  return createPortal(
    <div
      ref={ref}
      id={id}
      role="group"
      aria-label={label}
      onFocus={() => (focusInside.current = true)}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) focusInside.current = false;
      }}
      style={{ position: 'fixed', left: pos?.left ?? 0, top: pos?.top ?? 0, opacity: pos ? 1 : 0 }}
      className={cn('z-[70] w-48 rounded-xl border border-border bg-surface p-1 shadow-lg', className)}
    >
      {children}
    </div>,
    document.body,
  );
}
