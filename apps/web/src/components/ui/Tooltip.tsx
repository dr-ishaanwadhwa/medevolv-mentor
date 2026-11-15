'use client';

import {
  cloneElement,
  isValidElement,
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type FocusEvent,
  type PointerEvent,
  type ReactElement,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import { resolveTip, tipText, type TipProp } from '@/lib/tips';
import { computePosition, createTriggerController, tipStore } from './tooltip-logic';

type AnyProps = Record<string, unknown>;

/** Call the consumer's handler too: ours never replaces theirs. */
function chain<E>(ours: (e: E) => void, theirs: unknown): (e: E) => void {
  return (e) => {
    if (typeof theirs === 'function') (theirs as (e: E) => void)(e);
    ours(e);
  };
}

const noopSubscribe = () => () => {};

export function useOpen(id: string) {
  return (
    useSyncExternalStore(
      tipStore.subscribe,
      tipStore.get,
      () => null,
    ) === id
  );
}

/**
 * Tooltip behaviour for any trigger element. Returns `bind` (merge into the element's props),
 * `ref` (attach to it) and `node` (render next to it: persistent description + portal bubble).
 *
 * - hover 500 ms, keyboard focus at once, Escape closes, pointer may move onto the bubble;
 * - the description always exists (sr-only) and is referenced by aria-describedby;
 * - long-press (touch, icon-only buttons only) shows the tip; a plain tap or a synthetic click always activates.
 */
export function useTip(
  tip: TipProp | undefined,
  opts: { longPress?: boolean; disabled?: boolean } = {},
) {
  const uid = useId();
  const id = `tip${uid.replace(/:/g, '')}`;
  const descId = `${id}-d`;
  const resolved = resolveTip(tip);
  const [el, setEl] = useState<HTMLElement | null>(null);
  const controller = useMemo(
    () => createTriggerController(id, { longPress: !!opts.longPress }),
    [id, opts.longPress],
  );
  useEffect(() => () => controller.dispose(), [controller]);
  const open = useOpen(id);
  const text = resolved ? tipText(resolved, !!opts.disabled) : '';

  const bind = useCallback(
    (user: AnyProps = {}): AnyProps => {
      if (!resolved) return user;
      return {
        ...user,
        'aria-describedby': [user['aria-describedby'], descId].filter(Boolean).join(' '),
        onPointerEnter: chain((e: PointerEvent) => {
          if (e.pointerType !== 'touch') controller.hoverEnter();
        }, user.onPointerEnter),
        onPointerLeave: chain((e: PointerEvent) => {
          if (e.pointerType !== 'touch') controller.hoverLeave();
        }, user.onPointerLeave),
        onFocus: chain((e: FocusEvent<HTMLElement>) => {
          let visible = true;
          try {
            visible = e.currentTarget.matches(':focus-visible');
          } catch {
            /* old engines: treat as keyboard focus */
          }
          controller.focus(visible);
        }, user.onFocus),
        onBlur: chain(() => controller.blur(), user.onBlur),
        onPointerDown: chain((e: PointerEvent) => {
          if (e.pointerType === 'touch') controller.touchDown(e.clientX, e.clientY);
        }, user.onPointerDown),
        onPointerMove: chain((e: PointerEvent) => {
          if (e.pointerType === 'touch') controller.touchMove(e.clientX, e.clientY);
        }, user.onPointerMove),
        onPointerUp: chain((e: PointerEvent) => {
          if (e.pointerType === 'touch') controller.touchUp();
        }, user.onPointerUp),
        onPointerCancel: chain(() => controller.touchCancel(), user.onPointerCancel),
        // Only swallows the click that directly follows a long-press that showed the tip.
        // It never calls preventDefault, and a screen reader's synthetic click has no preceding long-press.
        onClickCapture: chain((e: { stopPropagation(): void }) => {
          if (controller.consumeSuppressedClick()) e.stopPropagation();
        }, user.onClickCapture),
      };
    },
    [resolved, descId, controller],
  );

  const node = resolved ? (
    <>
      <span id={descId} className="sr-only">
        {text}
      </span>
      {open && el ? <Bubble trigger={el} text={text} controller={controller} /> : null}
    </>
  ) : null;

  return { bind, ref: setEl, node, active: !!resolved };
}

export function Bubble({
  trigger,
  text,
  controller,
}: {
  trigger: HTMLElement;
  text: string;
  controller: ReturnType<typeof createTriggerController>;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  // Portal target exists only on the client; useSyncExternalStore keeps SSR output empty.
  const mounted = useSyncExternalStore(noopSubscribe, () => true, () => false);

  useLayoutEffect(() => {
    const place = () => {
      const b = ref.current;
      if (!b) return;
      const r = trigger.getBoundingClientRect();
      const p = computePosition(
        { top: r.top, left: r.left, width: r.width, height: r.height },
        { width: b.offsetWidth, height: b.offsetHeight },
        { width: window.innerWidth, height: window.innerHeight },
      );
      setPos({ top: p.top, left: p.left });
    };
    place();
    window.addEventListener('scroll', place, true);
    window.addEventListener('resize', place);
    return () => {
      window.removeEventListener('scroll', place, true);
      window.removeEventListener('resize', place);
    };
  }, [trigger, text]);

  // 120 ms fade, skipped under reduced motion.
  useEffect(() => {
    const b = ref.current;
    if (!b || typeof b.animate !== 'function') return;
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
    b.animate({ opacity: [0, 1] }, { duration: 120, easing: 'ease-out' });
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') controller.escape();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [controller]);

  if (!mounted) return null;
  return createPortal(
    <div
      ref={ref}
      role="tooltip"
      onPointerEnter={() => controller.bubbleEnter()}
      onPointerLeave={() => controller.bubbleLeave()}
      style={{
        position: 'fixed',
        top: pos?.top ?? 0,
        left: pos?.left ?? 0,
        visibility: pos ? 'visible' : 'hidden',
        maxWidth: 280,
      }}
      className="z-[80] rounded-lg bg-ink px-3 py-2 text-xs leading-snug text-bg shadow-pop"
    >
      {text}
    </div>,
    document.body,
  );
}

/** Merge two refs (the consumer's and ours). */
export function mergeRefs<T>(...refs: Array<React.Ref<T> | undefined>) {
  return (value: T | null) => {
    for (const r of refs) {
      if (typeof r === 'function') r(value);
      else if (r) (r as { current: T | null }).current = value;
    }
  };
}

/**
 * Wrap any single element (raw button, link, radio, role="option" ...) to give it a tip.
 * `iconOnly` enables long-press on touch and is for `<button>` only, never links.
 */
export function Tooltip({
  tip,
  iconOnly,
  disabled,
  children,
}: {
  tip: TipProp;
  iconOnly?: boolean;
  disabled?: boolean;
  children: ReactElement<AnyProps>;
}): ReactNode {
  const t = useTip(tip, { longPress: iconOnly, disabled });
  if (!isValidElement(children) || !t.active) return children;
  const child = children as ReactElement<AnyProps> & { ref?: React.Ref<HTMLElement> };
  const childRef = (child.props as AnyProps).ref as React.Ref<HTMLElement> | undefined;
  return (
    <>
      {cloneElement(child, { ...t.bind(child.props), ref: mergeRefs(childRef, t.ref) } as AnyProps)}
      {t.node}
    </>
  );
}
