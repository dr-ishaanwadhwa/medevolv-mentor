import type { Vector3 } from 'three';

/** A camera goal pose snapshot (what the scene is tweening towards). */
export interface PoseSnapshot {
  target: Vector3;
  position: Vector3;
}

export interface ViewState {
  selection: string[];
  isolate: boolean;
  goal: PoseSnapshot | null;
  /** part ids hidden with the Hide control */
  hidden: string[];
  /** explode amount, 0 (assembled) to 1 (every piece) */
  explode: number;
}

export interface ResetIntent {
  selection: string[];
  isolate: false;
  hidden: [];
  explode: 0;
  /** indices to frame; empty means the whole visible body (decision D-4) */
  frameParts: number[];
  /** what Undo restores */
  undo: ViewState;
}

/** Reset view = back to the fresh `/atlas` view: nothing selected, hidden or exploded. Layers and sex are not part of it. */
export function resetIntent(prev: ViewState): ResetIntent {
  return {
    selection: [],
    isolate: false,
    hidden: [],
    explode: 0,
    frameParts: [],
    undo: { selection: [...prev.selection], isolate: prev.isolate, goal: prev.goal, hidden: [...prev.hidden], explode: prev.explode },
  };
}

/** True when pressing Reset changes something worth an Undo toast. */
export function hasSomethingToUndo(prev: ViewState, cameraMoved: boolean): boolean {
  return prev.selection.length > 0 || prev.isolate || prev.hidden.length > 0 || prev.explode > 0 || cameraMoved;
}

/** Keep every query param except `select`, which is replaced (or removed when empty). */
export function withSelection(search: string, next: string[]): string {
  const p = new URLSearchParams(search);
  p.delete('select');
  const rest = p.toString();
  const sel = next.length ? `select=${next.map(encodeURIComponent).join(',')}` : '';
  const q = [sel, rest].filter(Boolean).join('&');
  return q ? `?${q}` : '';
}
