// Redirect checks for the landing switch (PRD 4.L test plan, 5.5 fallback when Playwright is not installed).
// Run against a production server you started yourself:  node scripts/check-redirects.mjs [http://127.0.0.1:3000]
const base = (process.argv[2] ?? 'http://127.0.0.1:3000').replace(/\/$/, '');

async function head(path, cookie) {
  const r = await fetch(base + path, { redirect: 'manual', headers: cookie ? { cookie } : {} });
  return { status: r.status, location: r.headers.get('location') ?? '', body: r.status === 200 ? await r.text() : '' };
}
const loc = (l) => (l.startsWith('http') ? new URL(l).pathname + new URL(l).search : l);

const checks = [
  ['/?q=x&go=1 -> /ask?q=x&go=1', async () => { const r = await head('/?q=x&go=1'); return [307, 308].includes(r.status) && loc(r.location) === '/ask?q=x&go=1'; }],
  ['/?q=x -> /ask?q=x', async () => { const r = await head('/?q=x'); return [307, 308].includes(r.status) && loc(r.location) === '/ask?q=x'; }],
  ['/ with mm_asked=1 -> /ask', async () => { const r = await head('/', 'mm_asked=1'); return r.status === 307 && loc(r.location) === '/ask'; }],
  ['/?tour=1 with mm_asked=1 -> 200 landing', async () => { const r = await head('/?tour=1', 'mm_asked=1'); return r.status === 200 && r.body.includes('id="landing-h1"'); }],
  ['/ new browser -> 200 landing with robots noindex', async () => { const r = await head('/'); return r.status === 200 && /<meta name="robots" content="noindex/.test(r.body); }],
  ['/ HTML never names the atlas manifest', async () => { const r = await head('/'); return r.status === 200 && !r.body.includes('/models/atlas.json'); }],
  ['/ask -> 200', async () => (await head('/ask')).status === 200],
];

let bad = 0;
for (const [name, fn] of checks) {
  let ok = false;
  try { ok = await fn(); } catch (e) { console.error(name, e.message); }
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}`);
  if (!ok) bad++;
}
process.exit(bad ? 1 : 0);
