'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { ChevronDown, EyeOff, Eye, Focus, Layers, Move3d, RotateCcw, Search, X } from 'lucide-react';
import { SYSTEMS, searchStructures, resolveHighlight, SUGGESTED_STRUCTURES, conceptName, normalizeFma } from '@/lib/anatomy';
import { anyHidden } from '@/lib/atlas-hidden';
import { explodeFamilyCount } from '@/lib/atlas-explode';
import { flattenGroups, groupSearchResults, systemLookup } from '@/lib/atlas-search';
import { useAtlasStore } from '@/lib/atlas-store';
import { hasSomethingToUndo, resetIntent, withSelection, type ViewState } from '@/lib/atlas-reset';
import {
  autoSwitchTarget,
  decideTarget,
  gzipTotalBytes,
  hasConcept,
  isConstrainedConnection,
  milestoneCrossed,
  otherSex,
  partitionSelection,
  readFemaleConfirmed,
  readSexPreference,
  sexLabel,
  withSex,
  withSexAndSelection,
  writeFemaleConfirmed,
  writeSexPreference,
  type Sex,
} from '@/lib/atlas-sex';
import { ATLAS_TIPS, layerTip, structureTip } from '@/lib/tips/atlas';
import { useUi } from '@/store/ui';
import { trackOnce } from '@/lib/api';
import { useFeature } from '@/components/FeaturesProvider';
import { ModelCredit } from '@/components/credits/ModelCredit';
import { Tooltip } from '@/components/ui/Tooltip';
import { NO_TIP } from '@/lib/tips/types';
import { cn } from '@/lib/cn';
import { Button, Chip } from '@/components/ui';
import AtlasCanvas, { type AtlasHit, type AtlasResolved } from './AtlasCanvas';
import type { AtlasCameraApi } from './AtlasScene';
import { SelectionPanel } from './SelectionPanel';
import { ExplodeControls } from './ExplodeControls';
import { FemaleNote, SexToggle } from './SexToggle';
import { DownloadProgress, FemaleConfirmSheet } from './FemaleDownload';

type SwitchHow = 'user' | 'auto' | 'cancel';
const UNDO_TIP = {
  purpose: 'Brings back your selection, Isolate and camera.',
  effect: 'Undoes Reset view. Shortcut: Ctrl or Cmd + Z while this message shows.',
};
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const parseSexParamIsFemale = () => new URLSearchParams(window.location.search).get('sex') === 'female';

export function AtlasView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const selectParam = params.get('select') ?? '';
  const sexParam = params.get('sex');
  const ids = useMemo(
    () => selectParam.split(',').map((s) => s.trim()).filter(Boolean).map(normalizeFma),
    [selectParam],
  );
  const idsKey = ids.join(',');

  // ---- which model (PRD 4.5 / D-8). Everything female is gated by the flag (F-9). ----
  const femaleFlag = useFeature('female_atlas');
  // localStorage is read after mount so server and client render the same markup.
  const [prefs, setPrefs] = useState<{ stored: Sex | null; confirmed: boolean } | null>(null);
  useEffect(() => setPrefs({ stored: readSexPreference(), confirmed: readFemaleConfirmed() }), []);
  const decision = decideTarget({ param: sexParam, hasSelect: ids.length > 0, flag: femaleFlag, stored: prefs?.stored ?? null });
  const confirmed = prefs?.confirmed ?? false;
  /** The model in the scene. A female request waits for the first-download confirm (F-8) and shows Male meanwhile. */
  const active: Sex = decision.target === 'female' && confirmed ? 'female' : 'male';

  const {
    atlases,
    indexes,
    statuses,
    loadManifest,
    isolate,
    setIsolate,
    hiddenParts,
    explode,
    setExplode,
    resetNonce,
    reset,
    visible,
    toggleSystem,
    resetLayers,
    setHiddenParts,
    progress,
    progressSex,
    modelReady,
    sceneError,
  } = useAtlasStore();
  const atlas = atlases[active];
  const index = indexes[active];
  useEffect(() => {
    void loadManifest(active);
  }, [loadManifest, active]);
  // Hidden structures and the explode amount belong to one model: a switch starts clean.
  useEffect(() => {
    const st = useAtlasStore.getState();
    st.setHiddenParts([]);
    st.setExplode(0);
  }, [active]);

  const replaceQuery = useCallback((q: string) => router.replace(`${pathname}${q}`, { scroll: false }), [router, pathname]);

  // Flag off: `?sex=` is ignored and removed, Male loads, no toast.
  useEffect(() => {
    if (decision.stripParam) replaceQuery(withSex(window.location.search, null));
  }, [decision.stripParam, replaceQuery]);

  // Layers lists only the systems the loaded model actually has (the female model adds two, the male has neither).
  const presentSystems = useMemo(() => new Set(atlas?.parts.map((p) => p.system) ?? []), [atlas]);

  const [resolved, setResolved] = useState<AtlasResolved | null>(null);
  const [activeIdx, setActiveIdx] = useState(0);
  const [layersOpen, setLayersOpen] = useState(false);
  const [explodeOpen, setExplodeOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [wide, setWide] = useState(true);
  const [sheetH, setSheetH] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setActiveIdx(0);
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
      replaceQuery(withSelection(window.location.search, next));
    },
    [replaceQuery],
  );

  const toast = useUi((s) => s.toast);
  const dismissToast = useUi((s) => s.dismiss);

  // ---- model switch ----
  const [pending, setPending] = useState<{ carry: string[]; how: SwitchHow } | null>(null);
  const [dismissedUrlAsk, setDismissedUrlAsk] = useState(false);
  const femaleRadio = useRef<HTMLButtonElement>(null);
  /** The selection the user said "Not now" to: the auto-switch does not ask again for it on this page. */
  const declinedAutoFor = useRef<string | null>(null);

  /** Switch the scene to `target`, carrying the selection by concept id (F-3). Assumes the female download is confirmed. */
  const switchTo = useRef<(target: Sex, carry: string[], how: SwitchHow) => Promise<void>>(async () => {});
  switchTo.current = async (target, carry, how) => {
    await loadManifest(target);
    const st = useAtlasStore.getState();
    const tAtlas = st.atlases[target];
    if (!tAtlas) {
      if (target === 'female') {
        toast("Couldn't load the female model.");
        writeSexPreference('male');
        replaceQuery(withSex(window.location.search, 'male'));
      }
      return;
    }
    const { keep, dropped } = how === 'auto' ? { keep: carry, dropped: [] as string[] } : partitionSelection(carry, tAtlas, st.indexes[target]);
    writeSexPreference(target);
    if (how !== 'cancel') trackOnce('atlas_sex_switch', { to: target }); // PRD 2.3 "Female atlas use"
    setPrefs((p) => ({ stored: target, confirmed: p?.confirmed ?? false }));
    replaceQuery(withSexAndSelection(window.location.search, target, keep));
    if (!keep.length) setIsolate(false);
    const from = otherSex(target);
    if (how === 'auto') {
      const name = conceptName(tAtlas, st.indexes[target], carry.find((id) => hasConcept(tAtlas, st.indexes[target], id)) ?? carry[0]);
      toast(`${cap(name)} is only in the ${sexLabel(target)} model, so it opened there.`, {
        action: { label: 'Switch back', onClick: () => requestSwitch(from, carry, 'user') },
      });
    } else if (dropped.length && how === 'user') {
      const name = conceptName(st.atlases[from], st.indexes[from], dropped[0]);
      toast(`${cap(name)} is only in the ${sexLabel(from)} model.`, {
        action: { label: 'Switch back', onClick: () => requestSwitch(from, carry, 'user') },
      });
    }
  };

  /** Entry point for every switch: the first female download asks first. */
  const requestSwitch = (target: Sex, carry: string[], how: SwitchHow) => {
    if (!femaleFlag) return;
    if (target === 'female' && !readFemaleConfirmed()) {
      void loadManifest('female'); // the sheet shows the size from the manifest
      setPending({ carry, how });
      return;
    }
    void switchTo.current(target, carry, how);
  };

  // A URL (link, stored choice) that asks for Female before the first download was confirmed also asks first.
  const urlAsks = femaleFlag && prefs !== null && decision.target === 'female' && !confirmed && !dismissedUrlAsk;
  const sheetOpen = femaleFlag && (pending !== null || urlAsks);
  useEffect(() => {
    if (urlAsks) void loadManifest('female');
  }, [urlAsks, loadManifest]);

  const closeSheet = () => {
    setPending(null);
    requestAnimationFrame(() => femaleRadio.current?.focus());
  };
  const onDownload = () => {
    writeFemaleConfirmed();
    setPrefs((p) => ({ stored: p?.stored ?? null, confirmed: true }));
    const p = pending;
    closeSheet();
    if (p) void switchTo.current('female', p.carry, p.how);
    else writeSexPreference('female');
  };
  const onNotNow = () => {
    declinedAutoFor.current = idsKey;
    if (urlAsks) {
      setDismissedUrlAsk(true);
      replaceQuery(withSex(window.location.search, 'male'));
    }
    closeSheet();
  };

  // Symmetric auto-switch: a `?select=` that names a structure missing here but present in the other model.
  useEffect(() => {
    if (!femaleFlag || !ids.length || !atlas || !index || sheetOpen) return;
    if (declinedAutoFor.current === idsKey) return;
    declinedAutoFor.current = null;
    if (ids.some((id) => hasConcept(atlas, index, id))) return;
    const other = otherSex(active);
    let cancelled = false;
    void loadManifest(other).then(() => {
      if (cancelled) return;
      const st = useAtlasStore.getState();
      const t = autoSwitchTarget(active, ids, { atlas, index }, { atlas: st.atlases[other], index: st.indexes[other] });
      if (t) requestSwitch(t, ids, 'auto');
    });
    return () => {
      cancelled = true;
    };
    // requestSwitch is a fresh closure each render; the inputs that matter are listed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [femaleFlag, idsKey, atlas, index, active, sheetOpen, loadManifest]);

  // Female manifest or geometry failed: say so and stay on Male (never the male model labelled Female).
  const femaleFailed = active === 'female' && (statuses.female === 'error' || sceneError?.sex === 'female');
  useEffect(() => {
    if (!femaleFailed) return;
    toast("Couldn't load the female model.");
    writeSexPreference('male');
    setPrefs((p) => ({ stored: 'male', confirmed: p?.confirmed ?? false }));
    replaceQuery(withSex(window.location.search, 'male'));
  }, [femaleFailed, toast, replaceQuery]);

  // The female manifest failed while the confirm sheet waits for its size: close the sheet, stay on Male.
  const sheetManifestFailed = sheetOpen && statuses.female === 'error';
  useEffect(() => {
    if (!sheetManifestFailed) return;
    toast("Couldn't load the female model.");
    setPending(null);
    setDismissedUrlAsk(true);
    if (parseSexParamIsFemale()) replaceQuery(withSex(window.location.search, 'male'));
  }, [sheetManifestFailed, toast, replaceQuery]);

  // ---- female download progress + milestone announcements (25/50/75, then ready) ----
  const downloading = active === 'female' && modelReady !== 'female' && !femaleFailed;
  const femalePct = progressSex === 'female' ? progress : 0;
  const [announce, setAnnounce] = useState('');
  const lastPct = useRef(0);
  const wasDownloading = useRef(false);
  useEffect(() => {
    if (!downloading) {
      if (wasDownloading.current && modelReady === 'female') setAnnounce('Female model ready');
      wasDownloading.current = false;
      lastPct.current = 0;
      return;
    }
    wasDownloading.current = true;
    const m = milestoneCrossed(lastPct.current, femalePct);
    lastPct.current = femalePct;
    if (m) setAnnounce(`Female model ${m}% downloaded`);
  }, [downloading, femalePct, modelReady]);

  // ---- Reset view (R4) ----
  const cameraApi = useRef<AtlasCameraApi | null>(null);
  const doReset = useCallback(() => {
    if (!atlas) return; // RV-7: nothing to reset before the manifest has loaded
    const prev: ViewState = { selection: ids, isolate, goal: cameraApi.current?.getGoal() ?? null, hidden: hiddenParts, explode };
    const intent = resetIntent(prev);
    const undoable = hasSomethingToUndo(prev, cameraApi.current?.hasMoved() ?? false);
    setSelection(intent.selection);
    reset(); // store: isolate off + bumps resetNonce; the scene then frames this model's default view
    if (!undoable) return; // nothing to undo, no toast
    let toastId = 0;
    const undo = () => {
      undoRef.current = null;
      setSelection(intent.undo.selection);
      setIsolate(intent.undo.isolate);
      setHiddenParts(intent.undo.hidden);
      setExplode(intent.undo.explode);
      // The selection reaches the scene a frame or two later; restoreGoal waits for it so its framing does not win.
      if (intent.undo.goal) cameraApi.current?.restoreGoal(intent.undo.goal, intent.undo.selection);
    };
    toastId = toast('View reset', { ms: 5000, action: { label: 'Undo', onClick: undo, tip: UNDO_TIP } });
    // Keyboard route to Undo while the toast is live (focus stays on Reset view, the toast is far away in tab order).
    undoRef.current = { run: () => { undo(); dismissToast(toastId); }, id: toastId };
  }, [atlas, ids, isolate, hiddenParts, explode, reset, setIsolate, setHiddenParts, setExplode, setSelection, toast, dismissToast]);

  const undoRef = useRef<{ run: () => void; id: number } | null>(null);
  const liveToastIds = useUi((s) => s.toasts.map((t) => t.id).join(','));
  useEffect(() => {
    // the Undo toast timed out or was dismissed: the shortcut goes with it
    if (undoRef.current && !liveToastIds.split(',').includes(String(undoRef.current.id))) undoRef.current = null;
  }, [liveToastIds]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!undoRef.current || !(e.metaKey || e.ctrlKey) || e.shiftKey || e.altKey || e.key.toLowerCase() !== 'z') return;
      const el = e.target as HTMLElement | null;
      if (el && (el.isContentEditable || el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) return; // the field's own undo
      e.preventDefault();
      undoRef.current.run();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const onSelect = useCallback((hit: AtlasHit) => setSelection([hit.fmaId]), [setSelection]);
  const hasSelection = ids.length > 0;

  // ---- hide / restore ----
  const selectedPartIds = useMemo(() => {
    if (!atlas || !index || !ids.length) return [];
    return resolveHighlight(atlas, index, ids).partIdx.map((i) => atlas.parts[i].id);
  }, [atlas, index, ids]);
  const doHide = () => {
    if (!selectedPartIds.length) return;
    useAtlasStore.getState().hideParts(selectedPartIds);
    setIsolate(false);
    setSelection([]);
  };
  // A structure that is selected is never also hidden: choosing it (search, chip, link, Back button) brings it back.
  useEffect(() => {
    const st = useAtlasStore.getState();
    if (selectedPartIds.length && anyHidden(st.hiddenParts, selectedPartIds)) st.revealParts(selectedPartIds);
    // only a change of selection reveals; hiding keeps the selection until the URL catches up
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey]);
  const familyCount = useMemo(() => (atlas ? explodeFamilyCount(atlas.parts) : 0), [atlas]);
  const sceneReady = modelReady === active;

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
  const bySystem = useMemo(() => (atlas ? systemLookup(atlas) : new Map()), [atlas]);
  const groups = useMemo(() => (atlas ? groupSearchResults(searchStructures(atlas, q, 24), bySystem) : []), [atlas, q, bySystem]);
  const results = useMemo(() => flattenGroups(groups), [groups]);
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
  const activeId = ids[Math.min(activeIdx, ids.length - 1)] ?? '';
  const constrained = typeof navigator !== 'undefined' && isConstrainedConnection((navigator as Navigator & { connection?: { saveData?: boolean; effectiveType?: string } }).connection);

  return (
    <div className="relative h-page overflow-hidden bg-[radial-gradient(ellipse_at_50%_35%,rgb(var(--c-surface))_0%,rgb(var(--c-bg))_72%)]">
      {prefs !== null && (
        <AtlasCanvas
          key={active /* one model in the scene at a time: a switch disposes the old scene */}
          className="absolute inset-0"
          sex={active}
          hideLoading={active === 'female'}
          highlight={ids}
          isolate={isolate}
          resetNonce={resetNonce}
          cameraApiRef={cameraApi}
          visibleSystems={visible}
          hiddenParts={hiddenParts}
          explode={explode}
          inset={inset}
          onSelect={onSelect}
          onResolved={setResolved}
          autoRotate={false}
        />
      )}

      {downloading && (
        <DownloadProgress
          label="Loading the female model"
          pct={femalePct}
          totalBytes={gzipTotalBytes(atlases.female)}
          onCancel={() => void switchTo.current('male', ids, 'cancel')}
        />
      )}
      <p className="sr-only" role="status" aria-live="polite">
        {announce}
      </p>

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
            <Tooltip tip={ATLAS_TIPS['atlas.search.clear']} iconOnly>
              <button
                type="button"
                aria-label="Clear search"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => setQ('')}
                className="absolute right-0 top-1/2 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-lg text-muted hover:bg-surface2 md:right-1.5 md:h-8 md:w-8"
              >
                <X className="h-4 w-4" />
              </button>
            </Tooltip>
          )}
          {open && results.length > 0 && (
            <ul
              id="atlas-results"
              role="listbox"
              className="absolute inset-x-0 top-full z-30 mt-1.5 max-h-72 overflow-y-auto rounded-xl border border-border bg-surface py-1 shadow-pop"
            >
              {groups.map((g) => (
                <li key={g.system} role="group" aria-label={g.name}>
                  <div className="label-mono sticky top-0 z-10 flex items-center gap-2 bg-surface px-3.5 py-1.5" aria-hidden>
                    <span className="h-2 w-2 rounded-full" style={{ background: SYSTEMS.find((x) => x.id === g.system)?.color }} />
                    {g.name}
                  </div>
                  <ul role="presentation">
                    {g.items.map((c) => {
                      const i = results.indexOf(c);
                      return (
                        <Tooltip key={c.id} tip={structureTip(c.name)}>
                          <li
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
                        </Tooltip>
                      );
                    })}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="pointer-events-auto flex flex-wrap items-center gap-2">
          {femaleFlag && (
            <SexToggle
              value={active}
              onChange={(next) => requestSwitch(next, ids, 'user')}
              femaleRef={femaleRadio}
              describedBy={active === 'female' ? 'atlas-female-note' : undefined}
            />
          )}
          <Button
            size="md"
            variant={isolate ? 'primary' : 'secondary'}
            onClick={() => setIsolate(!isolate)}
            disabled={!hasSelection}
            aria-pressed={isolate}
            tip={ATLAS_TIPS['atlas.isolate']}
            className="bg-opacity-95 px-3 text-sm shadow-card md:min-h-[32px]"
          >
            <Focus className="h-4 w-4" aria-hidden /> Isolate
          </Button>
          <Button
            size="md"
            variant="secondary"
            onClick={doHide}
            disabled={!selectedPartIds.length}
            tip={ATLAS_TIPS['atlas.hide']}
            className="px-3 text-sm shadow-card md:min-h-[32px]"
          >
            <EyeOff className="h-4 w-4" aria-hidden /> Hide
          </Button>
          {hiddenParts.length > 0 && (
            <Button
              size="md"
              variant="secondary"
              onClick={() => setHiddenParts([])}
              tip={ATLAS_TIPS['atlas.hide.restore']}
              className="px-3 text-sm shadow-card md:min-h-[32px]"
            >
              <Eye className="h-4 w-4" aria-hidden /> Restore ({hiddenParts.length})
            </Button>
          )}
          <Button size="md" variant="secondary" onClick={doReset} disabled={!atlas} tip={ATLAS_TIPS['atlas.reset']} className="px-3 text-sm shadow-card md:min-h-[32px]">
            <RotateCcw className="h-4 w-4" aria-hidden /> Reset view
          </Button>
          <Button
            size="md"
            variant={layersOpen ? 'primary' : 'secondary'}
            onClick={() => setLayersOpen((v) => !v)}
            aria-expanded={layersOpen}
            tip={ATLAS_TIPS['atlas.layers']}
            className="px-3 text-sm shadow-card md:min-h-[32px]"
          >
            <Layers className="h-4 w-4" aria-hidden /> Layers
          </Button>
          <Button
            size="md"
            variant={explodeOpen || explode > 0 ? 'primary' : 'secondary'}
            onClick={() => setExplodeOpen((v) => !v)}
            disabled={!sceneReady}
            aria-expanded={explodeOpen}
            tip={ATLAS_TIPS['atlas.explode']}
            className="px-3 text-sm shadow-card md:min-h-[32px]"
          >
            <Move3d className="h-4 w-4" aria-hidden /> Explode
          </Button>
        </div>

        {femaleFlag && active === 'female' && (
          <div className="pointer-events-auto">
            <FemaleNote id="atlas-female-note" />
          </div>
        )}

        {explodeOpen && sceneReady && <ExplodeControls amount={explode} familyCount={familyCount} onChange={setExplode} />}

        {layersOpen && (
          <div className="pointer-events-auto card p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="label-mono">Body systems</span>
              <Tooltip tip={ATLAS_TIPS['atlas.layers.default']}>
                <button type="button" onClick={resetLayers} className="min-h-[44px] px-2 text-xs text-accent underline-offset-2 hover:underline md:min-h-0">
                  Default
                </button>
              </Tooltip>
            </div>
            <div className="flex max-h-48 flex-wrap gap-1.5 overflow-y-auto">
              {SYSTEMS.filter((s) => s.id !== 'integumentary' && presentSystems.has(s.id)).map((s) => {
                const on = visible.includes(s.id);
                return (
                  <Tooltip key={s.id} tip={layerTip(s.name, on)}>
                    <button
                      type="button"
                      aria-pressed={on}
                      onClick={() => toggleSystem(s.id)}
                      className={cn(
                        'inline-flex min-h-[44px] items-center gap-1.5 rounded-full border px-2.5 text-xs font-medium transition-colors md:min-h-[36px]',
                        on ? 'border-accent/40 bg-accent-soft text-ink' : 'border-border bg-surface text-muted opacity-70',
                      )}
                    >
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} aria-hidden />
                      {s.name}
                    </button>
                  </Tooltip>
                );
              })}
            </div>
          </div>
        )}

        {!hasSelection && suggestions.length > 0 && (
          <div className="pointer-events-auto flex flex-wrap gap-1.5">
            {suggestions.slice(0, wide ? 7 : 4).map((c) => (
              <Chip key={c.id} onClick={() => setSelection([c.id])} tip={structureTip(c.name)} className="text-[0.82rem] shadow-card">
                {c.name}
              </Chip>
            ))}
          </div>
        )}

        {/* C1: credit for the model on screen (CC BY 4.0). */}
        <div className="pointer-events-auto w-fit rounded-lg bg-surface/85 px-2 py-1 backdrop-blur">
          <ModelCredit model={active === 'female' ? 'hra-vh-f' : 'bodyparts3d'} />
        </div>
      </div>

      {/* Empty-state hint */}
      {!hasSelection && !downloading && (
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
            {/* On desktop the title is not a control (it only folds the mobile sheet), so it carries no tip there. */}
            <Tooltip tip={wide ? NO_TIP : ATLAS_TIPS['atlas.panel.toggle']}>
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
            </Tooltip>
            <div className="flex shrink-0 items-center">
              {!wide && (
                <Tooltip tip={collapsed ? ATLAS_TIPS['atlas.panel.expand'] : ATLAS_TIPS['atlas.panel.collapse']} iconOnly>
                  <button
                    type="button"
                    onClick={() => setCollapsed((c) => !c)}
                    aria-label={collapsed ? 'Expand details' : 'Collapse details'}
                    className="grid h-11 w-11 place-items-center rounded-xl text-muted hover:bg-surface2"
                  >
                    <ChevronDown className={cn('h-5 w-5 transition-transform', collapsed && 'rotate-180')} />
                  </button>
                </Tooltip>
              )}
              <Tooltip tip={ATLAS_TIPS['atlas.panel.clear']} iconOnly>
                <button
                  type="button"
                  onClick={() => setSelection([])}
                  aria-label="Clear selection"
                  className="grid h-11 w-11 place-items-center rounded-xl text-muted hover:bg-surface2 hover:text-ink"
                >
                  <X className="h-5 w-5" />
                </button>
              </Tooltip>
            </div>
          </div>
          {!(collapsed && !wide) && (
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-4">
              {ids.length > 1 && (
                <div className="mb-3 flex flex-wrap gap-1.5">
                  {ids.map((id, i) => {
                    const name = conceptName(atlas, index, id);
                    return (
                      <Chip
                        key={id}
                        onClick={() => setActiveIdx(i)}
                        aria-pressed={i === activeIdx}
                        tip={{ purpose: `Shows the details for ${name}.`, effect: 'The highlight stays on every selected structure.' }}
                        className={cn('text-[0.8rem]', i === activeIdx && 'border-accent bg-accent-soft')}
                      >
                        {name}
                      </Chip>
                    );
                  })}
                </div>
              )}
              {unmatched.length > 0 && resolved && resolved.matched.length === 0 && (
                <p className="mb-3 rounded-lg bg-warn-soft px-3 py-2 text-sm text-warn">
                  This structure is not part of the 3D model, so nothing is highlighted.
                </p>
              )}
              <SelectionPanel fmaId={activeId} sex={active} />
            </div>
          )}
        </div>
      )}

      {sheetOpen && (
        <FemaleConfirmSheet
          totalBytes={gzipTotalBytes(atlases.female)}
          constrained={constrained}
          onDownload={onDownload}
          onNotNow={onNotNow}
        />
      )}
    </div>
  );
}
