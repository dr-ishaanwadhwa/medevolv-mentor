'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { ChevronDown, Focus, Layers, RotateCcw, Search, X } from 'lucide-react';
import { SYSTEMS, searchStructures, SUGGESTED_STRUCTURES, conceptName, normalizeFma } from '@/lib/anatomy';
import { useAtlasStore } from '@/lib/atlas-store';
import { hasSomethingToUndo, resetIntent, withSelection, type ViewState } from '@/lib/atlas-reset';
import { useUi } from '@/store/ui';
import { cn } from '@/lib/cn';
import { Button, Chip } from '@/components/ui';
import AtlasCanvas, { type AtlasHit, type AtlasResolved } from './AtlasCanvas';
import type { AtlasCameraApi } from './AtlasScene';
import { SelectionPanel } from './SelectionPanel';

export function AtlasView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const selectParam = params.get('select') ?? '';
  const ids = useMemo(
    () => selectParam.split(',').map((s) => s.trim()).filter(Boolean).map(normalizeFma),
    [selectParam],
  );
  const idsKey = ids.join(',');

  const { atlas, index, loadManifest, isolate, setIsolate, resetNonce, reset, visible, toggleSystem, resetLayers, progress } =
    useAtlasStore();
  useEffect(() => {
    void loadManifest();
  }, [loadManifest]);

  const [resolved, setResolved] = useState<AtlasResolved | null>(null);
  const [active, setActive] = useState(0);
  const [layersOpen, setLayersOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [wide, setWide] = useState(true);
  const [sheetH, setSheetH] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setActive(0);
    setCollapsed(false);
  }, [idsKey]);

  useEffect(() => {
    const mq = matchMedia('(min-width: 768px)');
    const on = () => setWide(mq.matches);
    on();
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);

  const setSelection = useCallback(
    (next: string[]) => {
      // Replace only `select`; every other query param (e.g. ?sex=) is kept.
      const q = withSelection(window.location.search, next);
      router.replace(`${pathname}${q}`, { scroll: false });
    },
    [router, pathname],
  );

  const cameraApi = useRef<AtlasCameraApi | null>(null);
  const toast = useUi((s) => s.toast);
  const doReset = useCallback(() => {
    if (!atlas) return; // RV-7: nothing to reset before the manifest has loaded
    const prev: ViewState = { selection: ids, isolate, goal: cameraApi.current?.getGoal() ?? null };
    const intent = resetIntent(prev);
    const undoable = hasSomethingToUndo(prev, cameraApi.current?.hasMoved() ?? false);
    setSelection(intent.selection);
    reset(); // store: isolate off + bumps resetNonce; the scene then frames the whole visible body
    if (!undoable) return; // nothing to undo, no toast
    const undo = () => {
      setSelection(intent.undo.selection);
      setIsolate(intent.undo.isolate);
      if (intent.undo.goal) cameraApi.current?.setGoal(intent.undo.goal);
    };
    // TODO(WS-K, Wave 2): store/ui.ts toast() has no `action` yet. When it lands, call
    // toast('View reset', 5000, { label: 'Undo', onClick: undo }). Until then Undo is not reachable from the UI.
    void undo;
    toast('View reset', 5000);
  }, [atlas, ids, isolate, reset, setIsolate, setSelection, toast]);

  const onSelect = useCallback((hit: AtlasHit) => setSelection([hit.fmaId]), [setSelection]);
  const hasSelection = ids.length > 0;

  // Keep the camera framing clear of the panel.
  useEffect(() => {
    if (!hasSelection) {
      setSheetH(0);
      return;
    }
    const el = panelRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setSheetH(el.getBoundingClientRect().height));
    ro.observe(el);
    return () => ro.disconnect();
  }, [hasSelection, wide]);
  const inset = hasSelection ? (wide ? { right: 436 } : { bottom: sheetH }) : undefined;

  // ---- structure search ----
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const [cursor, setCursor] = useState(0);
  const results = useMemo(() => (atlas ? searchStructures(atlas, q, 8) : []), [atlas, q]);
  useEffect(() => setCursor(0), [q]);
  const pickStructure = (id: string) => {
    setSelection([id]);
    setQ('');
    setOpen(false);
    (document.activeElement as HTMLElement | null)?.blur?.();
  };
  const suggestions = useMemo(() => {
    if (!atlas) return [];
    return SUGGESTED_STRUCTURES.map((n) => atlas.concepts.find((c) => c.name.toLowerCase() === n && c.elements.length)).filter(
      (c): c is NonNullable<typeof c> => !!c,
    );
  }, [atlas]);

  const unmatched = resolved?.unmatched ?? [];
  const activeId = ids[Math.min(active, ids.length - 1)] ?? '';

  return (
    <div className="relative h-page overflow-hidden bg-[radial-gradient(ellipse_at_50%_35%,rgb(var(--c-surface))_0%,rgb(var(--c-bg))_72%)]">
      <AtlasCanvas
        className="absolute inset-0"
        highlight={ids}
        isolate={isolate}
        resetNonce={resetNonce}
        cameraApiRef={cameraApi}
        visibleSystems={visible}
        inset={inset}
        onSelect={onSelect}
        onResolved={setResolved}
        autoRotate={false}
      />

      {/* Search + controls */}
      <div className={cn('pointer-events-none absolute left-3 top-3 z-20 flex flex-col gap-2', wide ? 'w-[340px]' : 'right-3')}>
        <div className="pointer-events-auto relative">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
          <input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 120)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowDown') {
                e.preventDefault();
                setCursor((c) => Math.min(c + 1, results.length - 1));
              } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setCursor((c) => Math.max(c - 1, 0));
              } else if (e.key === 'Enter' && results[cursor]) {
                e.preventDefault();
                pickStructure(results[cursor].id);
              } else if (e.key === 'Escape') {
                setQ('');
                setOpen(false);
              }
            }}
            role="combobox"
            aria-expanded={open && results.length > 0}
            aria-controls="atlas-results"
            aria-label="Search anatomical structures"
            placeholder={atlas ? 'Search structures: heart, optic chiasm…' : 'Loading structures…'}
            disabled={!atlas}
            className="h-11 w-full rounded-xl border border-border bg-surface/95 pl-10 pr-10 text-[0.95rem] text-ink shadow-card outline-none backdrop-blur placeholder:text-muted focus:border-accent"
          />
          {q && (
            <button
              type="button"
              aria-label="Clear search"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => setQ('')}
              className="absolute right-1.5 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-lg text-muted hover:bg-surface2"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          {open && results.length > 0 && (
            <ul
              id="atlas-results"
              role="listbox"
              className="absolute inset-x-0 top-full z-30 mt-1.5 max-h-72 overflow-y-auto rounded-xl border border-border bg-surface py-1 shadow-pop"
            >
              {results.map((c, i) => (
                <li
                  key={c.id}
                  role="option"
                  aria-selected={i === cursor}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => pickStructure(c.id)}
                  onMouseEnter={() => setCursor(i)}
                  className={cn('flex min-h-[44px] cursor-pointer items-center justify-between gap-3 px-3.5 py-2 text-sm md:min-h-[38px]', i === cursor && 'bg-accent-soft')}
                >
                  <span className="truncate first-letter:uppercase">{c.name}</span>
                  <span className="shrink-0 font-mono text-[0.68rem] text-muted">{c.id}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="pointer-events-auto flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant={isolate ? 'primary' : 'secondary'}
            onClick={() => setIsolate(!isolate)}
            disabled={!hasSelection}
            aria-pressed={isolate}
            title={hasSelection ? 'Show only the selected structure' : 'Select a structure first'}
            className="bg-opacity-95 shadow-card"
          >
            <Focus className="h-4 w-4" aria-hidden /> Isolate
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={doReset}
            aria-disabled={!atlas || undefined}
            title={atlas ? 'Back to the whole-body view. Layers stay as set.' : 'Atlas still loading'}
            className="shadow-card"
          >
            <RotateCcw className="h-4 w-4" aria-hidden /> Reset view
          </Button>
          <Button size="sm" variant={layersOpen ? 'primary' : 'secondary'} onClick={() => setLayersOpen((v) => !v)} aria-expanded={layersOpen} className="shadow-card">
            <Layers className="h-4 w-4" aria-hidden /> Layers
          </Button>
        </div>

        {layersOpen && (
          <div className="pointer-events-auto card p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="label-mono">Body systems</span>
              <button type="button" onClick={resetLayers} className="text-xs text-accent underline-offset-2 hover:underline">
                Default
              </button>
            </div>
            <div className="flex max-h-48 flex-wrap gap-1.5 overflow-y-auto">
              {SYSTEMS.filter((s) => s.id !== 'integumentary').map((s) => {
                const on = visible.includes(s.id);
                return (
                  <button
                    key={s.id}
                    type="button"
                    aria-pressed={on}
                    onClick={() => toggleSystem(s.id)}
                    className={cn(
                      'inline-flex min-h-[36px] items-center gap-1.5 rounded-full border px-2.5 text-xs font-medium transition-colors',
                      on ? 'border-accent/40 bg-accent-soft text-ink' : 'border-border bg-surface text-muted opacity-70',
                    )}
                  >
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} aria-hidden />
                    {s.name}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {!hasSelection && suggestions.length > 0 && (
          <div className="pointer-events-auto flex flex-wrap gap-1.5">
            {suggestions.slice(0, wide ? 7 : 4).map((c) => (
              <Chip key={c.id} onClick={() => setSelection([c.id])} className="min-h-[36px] text-[0.82rem] shadow-card">
                {c.name}
              </Chip>
            ))}
          </div>
        )}
      </div>

      {/* Empty-state hint */}
      {!hasSelection && progress >= 0 && (
        <p className="pointer-events-none absolute bottom-3 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-full border border-border bg-surface/90 px-3 py-1.5 text-xs text-muted shadow-card backdrop-blur">
          Drag to orbit · pinch or scroll to zoom · tap a structure
        </p>
      )}

      {/* Selection panel: right card on desktop, bottom sheet on mobile. Non-modal so the canvas stays live. */}
      {hasSelection && (
        <div
          ref={panelRef}
          className={cn(
            'absolute z-20 flex flex-col overflow-hidden border border-border bg-surface shadow-pop',
            wide
              ? 'bottom-3 right-3 top-3 w-[420px] animate-slide-in-right rounded-2xl'
              : 'inset-x-0 bottom-0 animate-slide-in-up rounded-t-2xl pb-[env(safe-area-inset-bottom)]',
            !wide && (collapsed ? 'max-h-[88px]' : 'max-h-[48dvh]'),
          )}
          role="complementary"
          aria-label="Selected structure"
        >
          <div className="flex items-start justify-between gap-2 px-4 pb-2 pt-3">
            <button
              type="button"
              onClick={() => !wide && setCollapsed((c) => !c)}
              className={cn('min-w-0 flex-1 text-left', wide && 'cursor-default')}
              aria-expanded={wide ? undefined : !collapsed}
            >
              {!wide && <span className="mx-auto mb-2 block h-1 w-9 rounded-full bg-border" aria-hidden />}
              <span className="label-mono block">3D structure</span>
              <span className="block truncate text-lg font-semibold first-letter:uppercase">
                {conceptName(atlas, index, activeId)}
              </span>
            </button>
            <div className="flex shrink-0 items-center">
              {!wide && (
                <button
                  type="button"
                  onClick={() => setCollapsed((c) => !c)}
                  aria-label={collapsed ? 'Expand details' : 'Collapse details'}
                  className="grid h-11 w-11 place-items-center rounded-xl text-muted hover:bg-surface2"
                >
                  <ChevronDown className={cn('h-5 w-5 transition-transform', collapsed && 'rotate-180')} />
                </button>
              )}
              <button
                type="button"
                onClick={() => setSelection([])}
                aria-label="Clear selection"
                className="grid h-11 w-11 place-items-center rounded-xl text-muted hover:bg-surface2 hover:text-ink"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>
          {!(collapsed && !wide) && (
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-4">
              {ids.length > 1 && (
                <div className="mb-3 flex flex-wrap gap-1.5">
                  {ids.map((id, i) => (
                    <Chip
                      key={id}
                      onClick={() => setActive(i)}
                      aria-pressed={i === active}
                      className={cn('min-h-[34px] text-[0.8rem]', i === active && 'border-accent bg-accent-soft')}
                    >
                      {conceptName(atlas, index, id)}
                    </Chip>
                  ))}
                </div>
              )}
              {unmatched.length > 0 && resolved && resolved.matched.length === 0 && (
                <p className="mb-3 rounded-lg bg-warn-soft px-3 py-2 text-sm text-warn">
                  This structure is not part of the 3D model, so nothing is highlighted.
                </p>
              )}
              <SelectionPanel fmaId={activeId} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
