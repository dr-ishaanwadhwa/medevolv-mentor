'use client';

import { useEffect, useRef, type KeyboardEvent } from 'react';
import { Button } from '@/components/ui';
import { ATLAS_TIPS } from '@/lib/tips/atlas';
import { megabytes, progressText } from '@/lib/atlas-sex';

/**
 * First-download confirm sheet (F-8, F-10). Modal dialog: focus goes to "Download" (or to "Not now" on Save-Data / 2g / 3g),
 * Tab is trapped, Escape = "Not now". The parent returns focus to the Female radio when the sheet closes.
 */
export function FemaleConfirmSheet({
  totalBytes,
  constrained,
  onDownload,
  onNotNow,
}: {
  /** gzip bytes of the female chunks from the manifest; 0 while the manifest is still loading */
  totalBytes: number;
  constrained: boolean;
  onDownload: () => void;
  onNotNow: () => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const download = useRef<HTMLButtonElement>(null);
  const notNow = useRef<HTMLButtonElement>(null);
  const known = totalBytes > 0;

  useEffect(() => {
    (constrained ? notNow : download).current?.focus();
    // focus once on open
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      onNotNow();
      return;
    }
    if (e.key !== 'Tab') return;
    const items = [download.current, notNow.current].filter((x): x is HTMLButtonElement => !!x);
    if (!items.length) return;
    const i = items.indexOf(document.activeElement as HTMLButtonElement);
    const next = e.shiftKey ? (i <= 0 ? items.length - 1 : i - 1) : i === items.length - 1 ? 0 : i + 1;
    e.preventDefault();
    items[next].focus();
  };

  return (
    <div className="absolute inset-0 z-40 grid place-items-center bg-bg/60 p-4 backdrop-blur-[2px]">
      <div
        ref={box}
        role="dialog"
        aria-modal="true"
        aria-labelledby="female-sheet-title"
        aria-describedby="female-sheet-body"
        onKeyDown={onKey}
        className="w-full max-w-sm rounded-2xl border border-border bg-surface p-5 shadow-pop"
      >
        <h2 id="female-sheet-title" className="text-lg font-semibold">
          {known ? `Download the female model (about ${megabytes(totalBytes)} MB)?` : 'Download the female model?'}
        </h2>
        <p id="female-sheet-body" className="mt-2 text-sm leading-relaxed text-muted">
          {known ? 'Best on Wi-Fi. ' : 'Checking the size. '}
          It is saved on this device, so you only download it once. It is a male-derived body reshaped to a female form, with female organs from the Human Reference Atlas, for orientation only.
          {constrained ? ' Your connection looks slow or data-saving.' : ''}
        </p>
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <Button ref={notNow} variant="secondary" onClick={onNotNow} tip={ATLAS_TIPS['atlas.female.notNow']}>
            Not now
          </Button>
          <Button
            ref={download}
            variant="primary"
            onClick={onDownload}
            disabled={!known}
            tip={{ ...ATLAS_TIPS['atlas.female.download'], disabled: 'Checking the download size first.' }}
          >
            Download
          </Button>
        </div>
      </div>
    </div>
  );
}

/** Progress while a model downloads: role=progressbar with a text value and a Cancel that stays focusable. */
export function DownloadProgress({
  label,
  pct,
  totalBytes,
  onCancel,
}: {
  label: string;
  pct: number;
  totalBytes: number;
  onCancel: () => void;
}) {
  return (
    <div className="pointer-events-none absolute inset-0 z-30 grid place-items-center">
      <div className="pointer-events-auto flex w-64 flex-col items-center gap-3 rounded-2xl border border-border bg-surface/95 px-5 py-4 text-center shadow-card backdrop-blur">
        <span className="text-sm font-medium">{label}</span>
        <div
          className="h-1.5 w-full overflow-hidden rounded-full bg-surface2"
          role="progressbar"
          aria-label={label}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(pct)}
          aria-valuetext={totalBytes ? progressText(pct, totalBytes) : `${Math.round(pct)}%`}
        >
          <div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${Math.max(6, pct)}%` }} />
        </div>
        <span className="label-mono">{totalBytes ? progressText(pct, totalBytes) : `${Math.round(pct)}%`}</span>
        <Button size="sm" variant="secondary" onClick={onCancel} tip={ATLAS_TIPS['atlas.female.cancel']}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
