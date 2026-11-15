'use client';

import { useUi } from '@/store/ui';

export function Toaster() {
  const toasts = useUi((s) => s.toasts);
  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-[calc(var(--tabbar-h)+env(safe-area-inset-bottom)+0.75rem)] z-[60] flex flex-col items-center gap-2 px-4 md:bottom-6"
    >
      {toasts.map((t) => (
        <div key={t.id} className="pointer-events-auto animate-fade-up rounded-xl bg-ink px-4 py-2.5 text-sm text-bg shadow-pop">
          {t.text}
        </div>
      ))}
    </div>
  );
}
