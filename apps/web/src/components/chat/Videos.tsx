'use client';

import { useEffect, useRef, useState } from 'react';
import { ExternalLink, Flag, MoreVertical } from 'lucide-react';
import { Tooltip } from '@/components/ui';
import { useFeature } from '@/components/FeaturesProvider';
import { fetchVideos, sendFeedback, trackOnce, type VideoCard, type VideosResponse } from '@/lib/api';
import { QUICK_REVISION_S, VIDEOS_COPY as C, captionLine, cardLinkName, youtubeSearchUrl } from '@/lib/copy/videos';
import { ANSWER_TIPS as T } from '@/lib/tips/answer';
import { useUi } from '@/store/ui';

type State = { s: 'idle' } | { s: 'loading' } | { s: 'ready'; data: VideosResponse } | { s: 'fallback' } | { s: 'off' };

const EXT = { target: '_blank', rel: 'noopener noreferrer' } as const;

/**
 * Suggested videos (PRD 4.2). A sibling <section> AFTER the answer <article>, never inside it: external, unchecked
 * content that must not read as part of the cited answer. Absent when the `videos` flag is off (no request at all) or
 * when there is no topic. The request is made only when the section scrolls into view (D-3), with the topic label
 * only. Without a YouTube key, after a 429 or any failure, the section shows the search link (fallback, no error).
 */
export function Videos({ topic }: { topic: string | null | undefined }) {
  const on = useFeature('videos');
  const [st, setSt] = useState<State>({ s: 'idle' });
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!on || !topic) return;
    const el = ref.current;
    if (!el) return;
    let alive = true;
    const ctl = new AbortController();
    const go = () => {
      setSt({ s: 'loading' });
      void fetchVideos(topic, ctl.signal).then((r) => {
        if (!alive) return;
        if (r.kind === 'off') setSt({ s: 'off' });
        else if (r.kind === 'fallback') setSt({ s: 'fallback' });
        else setSt({ s: 'ready', data: r.data });
      });
    };
    const io =
      typeof IntersectionObserver === 'undefined'
        ? null
        : new IntersectionObserver(
            (entries) => {
              if (entries.some((e) => e.isIntersecting)) {
                io?.disconnect();
                go();
              }
            },
            { rootMargin: '120px' },
          );
    if (io) io.observe(el);
    else go();
    return () => {
      alive = false;
      io?.disconnect();
      ctl.abort();
    };
  }, [on, topic]);

  if (!on || !topic || st.s === 'off') return null;
  const search = st.s === 'ready' ? st.data.fallback_url : youtubeSearchUrl(topic);
  const cards = st.s === 'ready' ? st.data.videos : [];

  return (
    <section
      ref={ref}
      aria-label={C.section_label}
      className="rounded-2xl border border-dashed border-border bg-surface2/60 p-4 sm:p-5"
    >
      <header className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <h3 className="text-sm font-semibold">{C.heading}</h3>
        <Tooltip tip={T['answer.videos.youtube']}>
          <a href="https://www.youtube.com/" {...EXT} className="text-xs font-medium text-muted underline-offset-2 hover:underline">
            YouTube
          </a>
        </Tooltip>
      </header>
      <p className="mt-1 text-sm text-ink" title={C.info}>
        {C.label}
      </p>
      <p className="sr-only">{C.info}</p>
      <p className="mt-1 text-xs text-muted">
        <Tooltip tip={T['answer.videos.terms']}>
          <a href={C.terms_url} {...EXT} className="underline underline-offset-2 hover:text-ink">
            {C.terms}
          </a>
        </Tooltip>
        {' · '}
        <Tooltip tip={T['answer.legal.terms']}>
          <a href="/terms" className="underline underline-offset-2 hover:text-ink">
            Terms
          </a>
        </Tooltip>
        {' · '}
        <Tooltip tip={T['answer.legal.privacy']}>
          <a href="/privacy" className="underline underline-offset-2 hover:text-ink">
            Privacy
          </a>
        </Tooltip>
      </p>

      {(st.s === 'idle' || st.s === 'loading') && (
        <ul className="mt-3 flex snap-x gap-3 overflow-x-auto pb-1 md:grid md:grid-cols-4 md:overflow-visible" aria-busy="true" aria-label="Loading videos">
          {[0, 1, 2, 3].map((i) => (
            <li key={i} className="w-[42%] shrink-0 snap-start md:w-auto">
              <div className="aspect-video animate-pulse rounded-lg bg-border/60" />
              <div className="mt-2 h-3 w-4/5 animate-pulse rounded bg-border/60" />
              <div className="mt-1.5 h-3 w-1/2 animate-pulse rounded bg-border/60" />
            </li>
          ))}
        </ul>
      )}

      {cards.length > 0 && (
        <ul className="mt-3 flex snap-x gap-3 overflow-x-auto pb-1 md:grid md:grid-cols-4 md:overflow-visible" aria-label="Videos">
          {cards.map((v) => (
            <VideoItem key={v.video_id} v={v} />
          ))}
        </ul>
      )}

      {(st.s === 'ready' || st.s === 'fallback') && (
        <p className="mt-3 text-sm">
          <Tooltip tip={T['answer.videos.search']}>
            <a href={search} {...EXT} className="inline-flex min-h-[44px] items-center gap-1.5 font-medium text-accent hover:underline md:min-h-0">
              {cards.length ? C.search_more : `${C.search_for} ${topic}`}
              <ExternalLink className="h-3.5 w-3.5" aria-hidden />
            </a>
          </Tooltip>
        </p>
      )}
    </section>
  );
}

function VideoItem({ v }: { v: VideoCard }) {
  const toast = useUi((s) => s.toast);
  const [menu, setMenu] = useState(false);
  const [reported, setReported] = useState(false);
  const report = async () => {
    setMenu(false);
    try {
      await sendFeedback({ kind: 'video_bad', target_id: v.video_id.slice(0, 32) });
      setReported(true);
      toast('Thanks, the team will review this video');
    } catch {
      toast('Could not send the report');
    }
  };
  return (
    <li className="relative w-[42%] shrink-0 snap-start rounded-xl border border-transparent p-1 transition-shadow hover:border-border hover:shadow-sm md:w-auto">
      <Tooltip tip={T['answer.videos.watch']}>
        <a
          href={v.watch_url}
          {...EXT}
          aria-label={cardLinkName(v.title, v.channel_title, v.duration_label)}
          onClick={() => trackOnce('video_click')}
          className="block"
        >
          {/* Thumbnail shown unaltered (YouTube API terms): no overlay, no crop, no zoom. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={v.thumbnail_url}
            alt={v.title}
            width={320}
            height={180}
            loading="lazy"
            referrerPolicy="no-referrer"
            className="aspect-video w-full rounded-lg bg-border/40"
          />
          <span className="mt-2 line-clamp-2 block pr-9 text-sm font-medium leading-snug text-ink">{v.title}</span>
        </a>
      </Tooltip>
      <span className="mt-0.5 block truncate text-xs text-muted">{v.channel_title}</span>
      <span className="block text-xs text-muted">
        {captionLine(v.duration_label, v.view_count)}
        {v.long_lecture ? ` · ${C.long_lecture}` : v.duration_seconds < QUICK_REVISION_S ? ` · ${C.quick_revision}` : ''}
      </span>
      <div className="absolute right-0 top-[calc(56.25%+0.25rem)]">
        <Tooltip tip={T['answer.videos.menu']} iconOnly>
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={menu}
            aria-label={`Options for ${v.title}`}
            onClick={() => setMenu((m) => !m)}
            className="inline-flex h-11 w-11 items-center justify-center rounded-full text-muted hover:bg-surface hover:text-ink"
          >
            <MoreVertical className="h-4 w-4" aria-hidden />
          </button>
        </Tooltip>
        {menu && (
          <div role="menu" className="absolute right-0 z-10 mt-1 w-48 rounded-xl border border-border bg-surface p-1 shadow-lg">
            <Tooltip tip={T['answer.videos.report']}>
              <button
                type="button"
                role="menuitem"
                disabled={reported}
                onClick={report}
                className="flex min-h-[44px] w-full items-center gap-2 rounded-lg px-3 text-left text-sm hover:bg-surface2 disabled:opacity-50"
              >
                <Flag className="h-4 w-4" aria-hidden /> {reported ? 'Reported' : C.report}
              </button>
            </Tooltip>
          </div>
        )}
      </div>
    </li>
  );
}
