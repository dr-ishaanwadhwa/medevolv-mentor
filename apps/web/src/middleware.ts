import { NextResponse, type NextRequest } from 'next/server';
import { ASKED_COOKIE, returningRedirect } from '@/components/landing/returning';

/** `/` is the landing; returning askers skip it with no flash (PRD 4.L, D-5). `/?tour=1` always shows it. */
export function middleware(req: NextRequest) {
  const to = returningRedirect(req.nextUrl.pathname, req.nextUrl.searchParams, req.cookies.get(ASKED_COOKIE)?.value);
  if (!to) return NextResponse.next();
  return NextResponse.redirect(new URL(to, req.url), 307);
}

export const config = { matcher: ['/'] };
