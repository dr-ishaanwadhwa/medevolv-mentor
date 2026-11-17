# Feature flags read stale right after a deploy

**Observed** on 2026-11-16 and 2026-11-17 (four deploys, every time): after `deploy/v2/push.sh`, the first request to `/ask`
or `/atlas` served a page rendered with **all flags off** (no Flowchart chip, no videos, no Male/Female switch). A reload a
few seconds later showed the right flags.

**Cause** (as of `main@e9c1398`): the root layout reads flags server-side with a short revalidate (D-15,
`apps/web/src/lib/features.ts`), and `next build` pre-renders the static routes while the API is unreachable, so the
build-time HTML bakes in `NO_FEATURES`. ISR serves that stale HTML once, then regenerates.

**Workaround used**: reload once after each deploy (the QA step does this).

**Proper fix (not done yet)**: render the flag-dependent shell dynamically (`export const dynamic = 'force-dynamic'` on
the layout or the affected routes), or have the deploy script warm `/`, `/ask`, `/atlas` right after the web container
starts. Related: [ADR-002](../decisions/ADR-002-next-release-scope.md), D-9/D-15 in the
[PRD](../../prd/2026-11-15-next-release-prd.md).
