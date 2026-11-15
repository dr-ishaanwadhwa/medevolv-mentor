'use client';

import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState, useSyncExternalStore, type MouseEvent, type PointerEvent } from 'react';
import { Marked } from 'marked';
import { cn } from '@/lib/cn';
import { Bubble } from './Tooltip';
import { createTriggerController, tipStore, type TriggerController } from './tooltip-logic';

const esc = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

const safeHref = (href: string) => /^(https?:|mailto:|\/|#)/i.test(href.trim());

// Dedicated instance: raw HTML is escaped, never rendered; links are scheme-checked.
const md = new Marked({
  gfm: true,
  breaks: false,
  renderer: {
    html: ({ text }) => esc(text),
    link({ href, title, tokens }) {
      const inner = this.parser.parseInline(tokens);
      if (!safeHref(href)) return inner;
      return `<a href="${esc(href)}"${title ? ` title="${esc(title)}"` : ''} target="_blank" rel="noopener noreferrer">${inner}</a>`;
    },
    image: ({ text }) => esc(text),
  },
  extensions: [
    {
      // [3] or [1, 2] -> clickable citation chips
      name: 'cite',
      level: 'inline',
      start: (src: string) => src.indexOf('['),
      tokenizer(src: string) {
        const m = /^\[(\d{1,2}(?:\s*,\s*\d{1,2})*)\]/.exec(src);
        if (!m) return undefined;
        return { type: 'cite', raw: m[0], nums: m[1].split(',').map((x) => Number(x.trim())) };
      },
      renderer(token) {
        return (token.nums as number[])
          .map((n) => `<button type="button" class="cite-chip" data-cite="${n}" aria-label="Open source ${n}">${n}</button>`)
          .join('');
      },
    },
  ],
});

export function renderMarkdown(text: string): string {
  return md.parse(text, { async: false }) as string;
}

/**
 * Safe markdown. Inline [n] markers become chips; clicks call `onCite(n)`.
 *
 * The chips are HTML strings, so they get a delegated tooltip: one set of listeners on the container
 * reads `data-cite` and shows `citeTip(n)` (for example "Source 2: Harrison 22e, ch 12, p 345. Opens the source.").
 * Each chip also gets a hidden description for aria-describedby. Without `citeTip` the text is generic.
 */
export function Markdown({
  text,
  onCite,
  className,
  small,
  citeTip,
}: {
  text: string;
  onCite?: (n: number) => void;
  className?: string;
  small?: boolean;
  citeTip?: (n: number) => string | null | undefined;
}) {
  const html = useMemo(() => renderMarkdown(text), [text]);
  const uid = useId().replace(/:/g, '');
  const root = useRef<HTMLDivElement>(null);
  const anchors = useRef(new Map<string, { el: HTMLElement; text: string; ctrl: TriggerController }>());
  const openId = useSyncExternalStoreOpen();
  const [, bump] = useState(0);

  const describe = (n: number) => citeTip?.(n) || `Source ${n}. Opens the source.`;

  // Give every generated chip a key, a persistent description and an aria-describedby.
  useLayoutEffect(() => {
    const host = root.current;
    if (!host) return;
    const map = anchors.current;
    map.forEach((a) => a.ctrl.dispose());
    map.clear();
    host.querySelectorAll<HTMLElement>('[data-cite]').forEach((el, i) => {
      const n = Number(el.dataset.cite);
      const key = `tip${uid}c${i}`;
      const desc = document.createElement('span');
      desc.id = `${key}-d`;
      desc.className = 'sr-only';
      desc.textContent = describe(n);
      el.after(desc);
      el.setAttribute('aria-describedby', desc.id);
      el.dataset.tipKey = key;
      map.set(key, { el, text: desc.textContent, ctrl: createTriggerController(key, { longPress: true }) });
    });
    bump((x) => x + 1);
    return () => {
      map.forEach((a) => a.ctrl.dispose());
      map.clear();
      host.querySelectorAll('span.sr-only[id^="tip"]').forEach((d) => d.remove());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- describe is derived from citeTip
  }, [html, citeTip, uid]);

  const find = (target: EventTarget | null) => {
    const el = (target as HTMLElement | null)?.closest?.<HTMLElement>('[data-tip-key]');
    return el ? anchors.current.get(el.dataset.tipKey!) : undefined;
  };

  const onClick = (e: MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest<HTMLElement>('[data-cite]');
    if (el && onCite) onCite(Number(el.dataset.cite));
  };
  const touch = (e: PointerEvent) => e.pointerType === 'touch';

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') tipStore.close();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  const open = openId ? anchors.current.get(openId) : undefined;
  return (
    <>
      <div
        ref={root}
        className={cn('md', small && 'md-sm', className)}
        onClickCapture={(e) => {
          if (find(e.target)?.ctrl.consumeSuppressedClick()) e.stopPropagation();
        }}
        onClick={onClick}
        onPointerOver={(e) => !touch(e) && find(e.target)?.ctrl.hoverEnter()}
        onPointerOut={(e) => !touch(e) && find(e.target)?.ctrl.hoverLeave()}
        onFocus={(e) => {
          let visible = true;
          try {
            visible = (e.target as HTMLElement).matches(':focus-visible');
          } catch {
            /* treat as keyboard focus */
          }
          find(e.target)?.ctrl.focus(visible);
        }}
        onBlur={(e) => find(e.target)?.ctrl.blur()}
        onPointerDown={(e) => touch(e) && find(e.target)?.ctrl.touchDown(e.clientX, e.clientY)}
        onPointerMove={(e) => touch(e) && find(e.target)?.ctrl.touchMove(e.clientX, e.clientY)}
        onPointerUp={(e) => touch(e) && find(e.target)?.ctrl.touchUp()}
        onPointerCancel={(e) => find(e.target)?.ctrl.touchCancel()}
        // eslint-disable-next-line react/no-danger -- html is produced by marked with raw HTML escaped
        dangerouslySetInnerHTML={{ __html: html }}
      />
      {open && <Bubble trigger={open.el} text={open.text} controller={open.ctrl} />}
    </>
  );
}

function useSyncExternalStoreOpen() {
  return useSyncExternalStore(tipStore.subscribe, tipStore.get, () => null);
}
