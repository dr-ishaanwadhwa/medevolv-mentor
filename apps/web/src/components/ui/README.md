# UI kit (`@/components/ui`)

Import from `@/components/ui`. Colours are theme tokens (light/dark switch automatically) — never hard-code hex.

Tailwind colours: `bg surface surface2 ink muted border accent accent-soft accent-ink good(-soft) warn(-soft) bad(-soft)`.
Fonts: `font-sans` (Instrument Sans), `font-mono` (IBM Plex Mono). Utility classes (globals.css): `.card`, `.page`
(centred max-w-3xl column), `.label-mono` (small uppercase mono label), `.skeleton`, `.md` (markdown typography).

| Component | Use |
|---|---|
| `<Button variant="primary\|secondary\|ghost\|danger" size="sm\|md\|lg">` | 44px tall by default (touch target). `buttonClass()` gives the classes for custom elements; `<LinkButton href>` for links. |
| `<Chip href?>` / `<Tag>` | Pill action or link; `Tag` is a tiny non-interactive mono label (e.g. "navigation only"). |
| `<StatusPill tone="good\|warn\|bad\|info\|neutral">` | Status badge. `statusMeta(status)` maps backend answer status to `{label,tone,declined}`. |
| `<CitationChip n onClick cited?>` | Numbered source marker. |
| `<Markdown text onCite?>` | Safe markdown (raw HTML escaped, links scheme-checked). `[n]` becomes a clickable chip calling `onCite(n)`. |
| `<Drawer open onClose title eyebrow? footer?>` | Right panel on desktop, bottom sheet on mobile. Esc closes, focus is trapped and restored. |
| `<Skeleton className>` / `<SkeletonLines lines>` | Loading placeholders. |
| `useUi().toast("text", { ms?, action? })` (`@/store/ui`) | Toast; `<Toaster/>` is mounted in the shell. `action: { label: "Undo", onClick }` adds an inline button (stays 6 s by default). The old `toast(text, ms)` form still works. |
| `<Tooltip tip>` / `useTip(tip, { longPress? })` | Tooltip for any control. `tip` is a `TipId` from `@/lib/tips` or `{ purpose, effect, disabled? }`. Hover 500 ms, keyboard focus at once, Escape closes, persistent `aria-describedby` description, portal bubble, touch long-press only for icon-only `<button>`s (`iconOnly`). Wrap raw controls directly (`<Tooltip tip="x"><button/></Tooltip>`); kit controls take `tip` as a prop. |
| `<CoachMark id text live?>` | One-time dismissible hint on touch devices for non-obvious controls. Placed by the feature's owner; pass `live={false}` while the feature flag is off. |

Layout notes: the shell gives a left rail (>=768px) and a bottom tab bar (<768px). Pages render inside `<main>`; mobile
bottom space is already reserved (`.pb-tabbar`). Use the `.h-page` class for a full-viewport-height canvas region (accounts for mobile top bar, tab bar, safe area).
`/explore`, `/c`, `/atlas` are listed in the nav; `/c/*` highlights Explore.

## Tooltips (R3)

- Copy lives in `@/lib/tips/<feature>.ts` (`shell`, `why`, `explore`, `story`; `atlas`, `answer`, `landing` belong to their workstreams) and is merged in `@/lib/tips/index.ts`. Rules are in that file's header: do not repeat the label, state purpose and effect, plain words, about 20 words.
- `Button`, `LinkButton` and `Chip` require a `tip` (TypeScript enforces it; use `NO_TIP` plus a comment only when a control truly needs none). `CitationChip`'s `tip` is optional and falls back to "Source n. Opens the source." A disabled `Button` whose tip has a `disabled` reason stays focusable (`aria-disabled`) so the reason can be read; its click is suppressed.
- Remove native `title` where a tip exists.
- `node scripts/check-tips.mjs` fails on any control without a tip that is not in `scripts/tips-baseline.json`. The baseline is empty, so every new raw `<button>`, `<a>`, `<Link>` or role control needs a `<Tooltip>` wrapper or `data-tip-id`. `src/lib/tips/registry.test.ts` fails on an empty tip, an id defined in two feature files, or two ids with the same copy.
- `<Markdown citeTip={(n) => ...}>` gives the inline `[n]` chips a delegated tooltip with the real source pointer.
