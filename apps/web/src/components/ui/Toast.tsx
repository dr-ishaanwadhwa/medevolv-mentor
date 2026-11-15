'use client';

import { useUi } from '@/store/ui';
import { Tooltip } from './Tooltip';

export function Toaster() {
  const toasts = useUi((s) => s.toasts);
  const dismiss = useUi((s) => s.dismiss);
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-[calc(var(--tabbar-h)+env(safe-area-inset-bottom)+0.75rem)] z-[60] flex flex-col items-center gap-2 px-4 md:bottom-6"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className="pointer-events-auto flex animate-fade-up items-center gap-3 rounded-xl bg-ink px-4 py-2.5 text-sm text-bg shadow-pop"
        >
          <span>{t.text}</span>
          {t.action && (
            <Tooltip tip="shell.toast.action">
            <button
              type="button"
              onClick={() => {
                t.action?.onClick();
                dismiss(t.id);
              }}
              className="-my-1 -mr-2 min-h-[36px] rounded-lg px-3 text-sm font-semibold underline underline-offset-2 hover:bg-bg/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-bg"
            >
              {t.action.label}
            </button>
            </Tooltip>
          )}
        </div>
      ))}
    </div>
  );
}
