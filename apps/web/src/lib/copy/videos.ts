/**
 * Suggested-videos copy (PRD 4.2). The single source is shared/copy/videos.json, which api/videos.py mirrors for the
 * API `label`; `videos.test.ts` keeps this file equal to it (a Next bundle cannot import outside apps/web reliably).
 */

export const VIDEOS_COPY = {
  heading: 'Suggested videos on YouTube',
  section_label: 'Suggested videos from YouTube, not checked by MedEvolv',
  label: 'External videos from YouTube. Not from your textbooks and not checked by MedEvolv.',
  info: 'Suggested videos from YouTube. These are not from your textbooks, are not checked by MedEvolv, and may differ from the cited answer. Always trust the cited textbook passages first.',
  terms: "By using video suggestions you agree to YouTube's Terms of Service",
  terms_url: 'https://www.youtube.com/t/terms',
  search_more: 'Search YouTube for more',
  search_for: 'Search YouTube for',
  long_lecture: 'Long lecture',
  quick_revision: 'Quick revision',
  report: 'Report this video',
} as const;

export const QUICK_REVISION_S = 15 * 60;

const norm = (topic: string) => topic.trim().replace(/\s+/g, ' ').toLowerCase();

/** Same link the API builds (api/videos.py fallback_url): the topic label + " lecture MBBS", never question text. */
export function youtubeSearchUrl(topic: string): string {
  return `https://www.youtube.com/results?${new URLSearchParams({ search_query: `${norm(topic)} lecture MBBS` })}`;
}

/** "123K views", "1.2M views". */
export function viewsLabel(n: number): string {
  if (n >= 1_000_000) return `${trim(n / 1_000_000)}M views`;
  if (n >= 1_000) return `${trim(n / 1_000)}K views`;
  return `${n} views`;
}
const trim = (x: number) => (x >= 10 ? Math.round(x).toString() : x.toFixed(1).replace(/\.0$/, ''));

/** Caption under a card: "20:34 · 123K views". Duration goes here, never on the thumbnail (YouTube branding rules). */
export function captionLine(durationLabel: string, views: number): string {
  return `${durationLabel} · ${viewsLabel(views)}`;
}

/** Accessible name of a card link (PRD 4.2 accessibility). */
export function cardLinkName(title: string, channel: string, durationLabel: string): string {
  return `Video: ${title}, ${channel}, ${durationLabel}, opens YouTube in a new tab`;
}
