/** Returning-user rule (PRD 4.L, decision D-5): a browser that has had an answer (`mm_asked` cookie, written by the chat
 * when its first answer finishes) goes straight from `/` to `/ask`, on the server, unless `?tour=1` asks for the tour.
 * Pure so the unit test covers it; src/middleware.ts applies it. */

export const ASKED_COOKIE = 'mm_asked';

export function returningRedirect(pathname: string, search: URLSearchParams, asked: string | undefined): string | null {
  if (pathname !== '/') return null;
  if (search.get('tour') === '1') return null;
  if (search.has('q')) return null; // next.config.mjs redirects /?q= to /ask and keeps the query
  return asked === '1' ? '/ask' : null;
}
