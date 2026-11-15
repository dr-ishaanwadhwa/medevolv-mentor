'use client';

import { useMemo, type MouseEvent } from 'react';
import { Marked } from 'marked';
import { cn } from '@/lib/cn';

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

/** Safe markdown. Inline [n] markers become chips; clicks call `onCite(n)`. */
export function Markdown({
  text,
  onCite,
  className,
  small,
}: {
  text: string;
  onCite?: (n: number) => void;
  className?: string;
  small?: boolean;
}) {
  const html = useMemo(() => renderMarkdown(text), [text]);
  const onClick = (e: MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest<HTMLElement>('[data-cite]');
    if (el && onCite) onCite(Number(el.dataset.cite));
  };
  return (
    // eslint-disable-next-line react/no-danger -- html is produced by marked with raw HTML escaped
    <div className={cn('md', small && 'md-sm', className)} onClick={onClick} dangerouslySetInnerHTML={{ __html: html }} />
  );
}
