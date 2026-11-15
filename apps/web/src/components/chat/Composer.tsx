'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import { ArrowUp, Square } from 'lucide-react';
import { useChat } from '@/store/chat';

/** `above`: rendered inside the pinned area, so it stays visible while a long answer scrolls. */
export function Composer({ above }: { above?: ReactNode } = {}) {
  const { draft, setDraft, ask, busy, stop } = useChat();
  const ref = useRef<HTMLTextAreaElement>(null);

  // auto-grow up to ~6 lines
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 168)}px`;
  }, [draft]);

  const submit = () => {
    if (draft.trim() && !busy) ask(draft);
  };

  return (
    <div className="sticky bottom-[calc(var(--tabbar-h)+env(safe-area-inset-bottom))] z-20 bg-gradient-to-t from-bg from-70% to-transparent pb-3 pt-6 md:bottom-0">
      {above}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="card flex items-end gap-2 p-2 focus-within:border-accent/60"
      >
        <label htmlFor="composer" className="sr-only">
          Ask a question from the textbooks
        </label>
        <textarea
          id="composer"
          ref={ref}
          rows={1}
          value={draft}
          maxLength={2000}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Ask a clinical or basic-science question"
          className="max-h-[168px] min-h-[44px] flex-1 resize-none bg-transparent px-3 py-[11px] text-base leading-snug outline-none placeholder:text-muted/70"
        />
        {busy ? (
          <button
            type="button"
            onClick={stop}
            aria-label="Stop"
            className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-surface2 text-ink hover:bg-border"
          >
            <Square className="h-4 w-4 fill-current" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={!draft.trim()}
            aria-label="Send"
            className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-accent text-accent-ink transition-opacity disabled:opacity-35"
          >
            <ArrowUp className="h-5 w-5" />
          </button>
        )}
      </form>
      <p className="mt-1.5 hidden px-1 text-[0.72rem] text-muted sm:block">
        Enter to send, Shift+Enter for a new line. A study aid, not medical advice.
      </p>
    </div>
  );
}
