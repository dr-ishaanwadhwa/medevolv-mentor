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
| `useUi().toast("text")` (`@/store/ui`) | Toast; `<Toaster/>` is mounted in the shell. |

Layout notes: the shell gives a left rail (>=768px) and a bottom tab bar (<768px). Pages render inside `<main>`; mobile
bottom space is already reserved (`.pb-tabbar`). Use the `.h-page` class for a full-viewport-height canvas region (accounts for mobile top bar, tab bar, safe area).
`/explore`, `/c`, `/atlas` are listed in the nav; `/c/*` highlights Explore.
