'use client';

import { useUi } from '@/store/ui';
import { Button } from './Button';

/**
 * Toasts. The dismiss timer pauses while the pointer or keyboard focus is on a toast, and the action is a kit Button
 * (44 px target, its own tip) so callers can say what it does, for example Undo after Reset view.
 */
export function Toaster() {
  const toasts = useUi((s) => s.toasts);
  const dismiss = useUi((s) => s.dismiss);
  const pause = useUi((s) => s.pause);
  const resume = useUi((s) => s.resume);
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-[calc(var(--tabbar-h)+env(safe-area-inset-bottom)+0.75rem)] z-[60] flex flex-col items-center gap-2 px-4 md:bottom-6"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          onPointerEnter={() => pause(t.id)}
          onPointerLeave={() => resume(t.id)}
          onFocus={() => pause(t.id)}
          onBlur={(e) => {
            if (!e.currentTarget.contains(e.relatedTarget as Node | null)) resume(t.id);
          }}
          className="pointer-events-auto flex animate-fade-up items-center gap-3 rounded-xl bg-ink px-4 py-1.5 text-sm text-bg shadow-pop"
        >
          <span className="py-1">{t.text}</span>
          {t.action && (
            <Button
              size="md"
              variant="ghost"
              tip={t.action.tip ?? 'shell.toast.action'}
              onClick={() => {
                t.action?.onClick();
                dismiss(t.id);
              }}
              className="-my-1 -mr-2 px-3 text-sm font-semibold text-bg underline underline-offset-2 hover:bg-bg/10 hover:text-bg focus-visible:outline focus-visible:outline-2 focus-visible:outline-bg"
            >
              {t.action.label}
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}
