'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import * as T from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { AlertTriangle } from 'lucide-react';
import { SYSTEMS, resolveHighlight, type Atlas, type SystemId } from '@/lib/anatomy';
import { useAtlasStore } from '@/lib/atlas-store';
import { defaultFramingParts, type Sex } from '@/lib/atlas-sex';
import { computeGoalPose } from '@/lib/atlas-camera';
import type { PoseSnapshot } from '@/lib/atlas-reset';
import { cn } from '@/lib/cn';
import { PointerTap } from './pointer-tap';
import { loadChunk } from './model-download';

export interface AtlasHit {
  /** FMA concept id of the tapped part (matches ?select= and /api/spatial/resolve?fma=) */
  fmaId: string;
  name: string;
  partId: string;
}

export interface AtlasResolved {
  matched: string[];
  unmatched: string[];
  names: string[];
}

/** Imperative camera handle for the toolbar (Reset view / Undo). Filled by the scene once it is running. */
export interface AtlasCameraApi {
  getGoal: () => PoseSnapshot;
  setGoal: (p: PoseSnapshot) => void;
  /**
   * Restore `p` once the scene shows `highlight` (Undo after Reset view, RV-6). The selection reaches the scene a frame or
   * two after the URL update and its framing (and the panel inset) would otherwise overwrite the restored pose.
   */
  restoreGoal: (p: PoseSnapshot, highlight: string[]) => void;
  /** true once the user has orbited, panned or zoomed since the last framing */
  hasMoved: () => boolean;
}

export interface AtlasCanvasProps {
  /** FMA ids (or part ids) to highlight. Everything else is ghosted. Empty = whole body, nothing highlighted. */
  highlight?: string[];
  /** Show only the highlighted structures. */
  isolate?: boolean;
  /** Bump to reset the camera to the default whole-body (or whole-selection) view. */
  resetNonce?: number;
  /** Systems shown when nothing is isolated. Defaults to every system except the skin. */
  visibleSystems?: SystemId[];
  onSelect?: (hit: AtlasHit) => void;
  onResolved?: (r: AtlasResolved) => void;
  /** Free pixels the camera should keep clear (e.g. a side panel or bottom sheet overlaying the canvas). */
  inset?: { right?: number; bottom?: number };
  /** Small embed: load only the highlighted structures, no wheel zoom, vertical swipes scroll the page. */
  compact?: boolean;
  autoRotate?: boolean;
  /** Which model to show. Defaults to male: only the full atlas viewer ever asks for female (F-7). */
  sex?: Sex;
  /** The parent shows its own loading UI (the female download has size, cancel and announcements). */
  hideLoading?: boolean;
  /** Receives the camera handle (null on unmount). */
  cameraApiRef?: { current: AtlasCameraApi | null };
  className?: string;
}

const ACCENT = new T.Color('#27c4b0');
const FOV = 34;
const NO_GHOST = new Set<SystemId>(['muscular', 'connective', 'lymphatic', 'arterial', 'venous']);
const reducedMotion = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;

export default function AtlasScene(props: AtlasCanvasProps) {
  const { highlight, compact = false, className, sex = 'male' } = props;
  const atlas = useAtlasStore((s) => s.atlases[sex]);
  const index = useAtlasStore((s) => s.indexes[sex]);
  const status = useAtlasStore((s) => s.statuses[sex]);
  const loadError = useAtlasStore((s) => s.errors[sex]);
  const loadManifest = useAtlasStore((s) => s.loadManifest);
  const setStoreProgress = useAtlasStore((s) => s.setProgress);
  const setModelReady = useAtlasStore((s) => s.setModelReady);
  const setSceneError = useAtlasStore((s) => s.setSceneError);
  const host = useRef<HTMLDivElement>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);

  useEffect(() => {
    void loadManifest(sex);
  }, [loadManifest, sex]);

  const highlightKey = (highlight ?? []).join(',');
  const resolution = useMemo(
    () => (atlas && index ? resolveHighlight(atlas, index, highlight ?? []) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [atlas, index, highlightKey],
  );

  // Latest props, read inside the render loop.
  const latest = useRef(props);
  latest.current = props;
  const partIdxRef = useRef<number[]>([]);
  partIdxRef.current = resolution?.partIdx ?? [];

  const onResolved = props.onResolved;
  useEffect(() => {
    if (resolution && onResolved) onResolved({ matched: resolution.matched, unmatched: resolution.unmatched, names: resolution.names });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolution]);

  // In compact mode the scene is rebuilt per selection, since only those chunks are loaded.
  const sceneKey = compact ? highlightKey : '';

  useEffect(() => {
    if (!atlas || !host.current) return;
    const el = host.current;
    let disposed = false;
    let frame = 0;
    let dirty = true;
    setError('');
    setReady(false);
    setProgress(0);
    if (!compact) {
      setStoreProgress(0, sex);
      setModelReady(null);
      setSceneError(null);
    }
    // Only the female download is cancellable: its chunks are not shared with another viewer.
    const abort = new AbortController();
    const signal = sex === 'female' && !compact ? abort.signal : undefined;
    const fail = (message: string) => {
      setError(message);
      if (!compact) setSceneError({ sex, message });
    };

    let renderer: T.WebGLRenderer;
    try {
      renderer = new T.WebGLRenderer({ antialias: !compact, alpha: true, powerPreference: 'high-performance' });
    } catch {
      fail('This browser could not start the 3D viewer. Please try one with WebGL enabled.');
      return;
    }
    const mobile = () => el.clientWidth < 768;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, mobile() ? 1.5 : 2));
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = T.SRGBColorSpace;
    renderer.toneMapping = T.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    const canvas = renderer.domElement;
    canvas.style.display = 'block';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.setAttribute('role', 'img');
    canvas.setAttribute(
      'aria-label',
      `3D human anatomy, ${sex} reference model. Drag to orbit, pinch or scroll to zoom, tap a structure to inspect it.`,
    );
    el.appendChild(canvas);

    const scene = new T.Scene();
    const camera = new T.PerspectiveCamera(FOV, 1, 0.005, 100);
    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.09;
    controls.minDistance = 0.06;
    controls.maxDistance = 30;
    controls.maxPolarAngle = Math.PI * 0.96;
    controls.addEventListener('change', () => (dirty = true));
    if (compact) {
      controls.enableZoom = false;
      controls.enablePan = false;
      canvas.style.touchAction = 'pan-y';
    }

    const pmrem = new T.PMREMGenerator(renderer);
    const room = new RoomEnvironment();
    const envTarget = pmrem.fromScene(room, 0.04);
    scene.environment = envTarget.texture;
    room.dispose();
    pmrem.dispose();
    scene.add(new T.HemisphereLight(0xffffff, 0x9aa3a8, 1.0));
    const key = new T.DirectionalLight(0xfffaf4, 2.2);
    key.position.set(-2, 4, 3);
    scene.add(key);
    const rim = new T.DirectionalLight(0xe9f0ff, 1.6);
    rim.position.set(2, 2, -3);
    scene.add(rim);

    // Per-part state texture: r = visible, g = selected, b = ghost.
    const parts = atlas.parts;
    const n = parts.length;
    const stateData = new Uint8Array(n * 4);
    const stateTexture = new T.DataTexture(stateData, n, 1, T.RGBAFormat, T.UnsignedByteType);
    stateTexture.needsUpdate = true;

    const makeMaterial = (color: string, ghost: boolean) => {
      const m = new T.MeshStandardMaterial({
        color,
        metalness: 0.08,
        roughness: 0.55,
        side: T.DoubleSide,
        transparent: ghost,
        opacity: ghost ? 0.07 : 1,
        depthWrite: !ghost,
      });
      m.customProgramCacheKey = () => (ghost ? 'atlas-ghost' : 'atlas-solid');
      m.onBeforeCompile = (shader) => {
        shader.uniforms.partState = { value: stateTexture };
        shader.uniforms.stateWidth = { value: n };
        shader.uniforms.accent = { value: ACCENT };
        shader.vertexShader =
          'attribute float partIndex; uniform sampler2D partState; uniform float stateWidth; varying vec3 vPart;\n' +
          shader.vertexShader.replace(
            '#include <begin_vertex>',
            '#include <begin_vertex>\nvPart = texture2D(partState, vec2((partIndex + 0.5) / stateWidth, 0.5)).rgb;',
          );
        shader.fragmentShader =
          'varying vec3 vPart; uniform vec3 accent;\n' +
          shader.fragmentShader
            .replace(
              '#include <clipping_planes_fragment>',
              `#include <clipping_planes_fragment>\nif (vPart.r < 0.5 || ${ghost ? 'vPart.b < 0.5' : 'vPart.b > 0.5'}) discard;`,
            )
            .replace('#include <color_fragment>', '#include <color_fragment>\ndiffuseColor.rgb = mix(diffuseColor.rgb, accent, vPart.g * 0.55);')
            .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += accent * vPart.g * 0.16;');
      };
      return m;
    };
    const solid = new Map<string, T.MeshStandardMaterial>();
    const ghost = new Map<string, T.MeshStandardMaterial>();
    for (const s of SYSTEMS) {
      solid.set(s.id, makeMaterial(s.color, false));
      ghost.set(s.id, makeMaterial(s.color, true));
    }
    const ghostMeshes: T.Mesh[] = [];
    const geometries: T.BufferGeometry[] = [];
    const pickMaterial = new T.MeshBasicMaterial({ side: T.DoubleSide });
    const pickers: (T.Mesh | undefined)[] = new Array(n);
    const bounds = parts.map((p) => new T.Box3(new T.Vector3().fromArray(p.bounds[0]), new T.Vector3().fromArray(p.bounds[1])));

    let stateKey = '';

    // Which parts/chunks do we need?
    const wanted = new Set<number>();
    if (compact) partIdxRef.current.forEach((i) => wanted.add(i));
    else parts.forEach((p, i) => wanted.add(i));
    for (const i of [...wanted]) if (parts[i].system === 'integumentary') wanted.delete(i);
    const chunkIds = [...new Set([...wanted].map((i) => parts[i].chunk))];
    const loadedParts = new Set<number>();

    const buildChunk = async (ci: number) => {
      const buffer = await loadChunk(atlas, atlas.chunks[ci], signal);
      if (disposed) return;
      const groups = new Map<string, T.BufferGeometry[]>();
      parts.forEach((p, i) => {
        if (p.chunk !== ci || !wanted.has(i)) return;
        const g = new T.BufferGeometry();
        g.setAttribute('position', new T.BufferAttribute(new Float32Array(buffer, p.positions, p.vertexCount * 3), 3));
        g.setAttribute('normal', new T.BufferAttribute(new Int16Array(buffer, p.normals, p.vertexCount * 3), 3, true));
        g.setIndex(new T.BufferAttribute(new Uint32Array(buffer, p.indices, p.indexCount), 1));
        g.boundingBox = bounds[i].clone();
        g.computeBoundingSphere();
        const pick = new T.Mesh(g, pickMaterial);
        pick.matrixAutoUpdate = false;
        pickers[i] = pick;
        geometries.push(g);
        g.setAttribute('partIndex', new T.BufferAttribute(new Float32Array(p.vertexCount).fill(i), 1));
        const list = groups.get(p.system) ?? [];
        list.push(g);
        groups.set(p.system, list);
        loadedParts.add(i);
      });
      groups.forEach((gs, system) => {
        const merged = mergeGeometries(gs, false);
        if (!merged) return;
        geometries.push(merged);
        const m = new T.Mesh(merged, solid.get(system));
        m.frustumCulled = false;
        scene.add(m);
        const gm = new T.Mesh(merged, ghost.get(system));
        gm.frustumCulled = false;
        gm.renderOrder = 2;
        ghostMeshes.push(gm);
        scene.add(gm);
      });
      stateKey = '';
      dirty = true;
    };

    let done = 0;
    let cursor = 0;
    const worker = async () => {
      while (cursor < chunkIds.length && !disposed) {
        const ci = chunkIds[cursor++];
        await buildChunk(ci);
        done++;
        if (!disposed) {
          const pct = Math.round((done / chunkIds.length) * 100);
          setProgress(pct);
          if (!compact) setStoreProgress(pct, sex);
        }
      }
    };
    void Promise.all(Array.from({ length: Math.min(3, Math.max(1, chunkIds.length)) }, worker))
      .then(() => {
        if (disposed) return;
        setReady(true);
        if (!compact) setModelReady(sex);
        stateKey = '';
        dirty = true;
      })
      .catch((e) => {
        if (!disposed) fail(e instanceof Error ? e.message : 'Could not load the anatomy.');
      });
    if (!chunkIds.length) {
      setReady(true);
      if (!compact) setModelReady(sex);
    }

    // ---- camera framing ----
    const goalTarget = new T.Vector3(0, 0.85, 0);
    const goalPos = new T.Vector3(1.2, 1.1, 3.4);
    let tweening = false;
    let userMoved = false;
    controls.addEventListener('start', () => {
      tweening = false;
      userMoved = true;
    });

    const applyInset = () => {
      const w = el.clientWidth;
      const h = el.clientHeight;
      const r = latest.current.inset?.right ?? 0;
      const b = latest.current.inset?.bottom ?? 0;
      if (r || b) camera.setViewOffset(w, h, r / 2, b / 2, w, h);
      else camera.clearViewOffset();
    };

    // Per-model default view (D-4 per model): male frames the whole body, female the torso and pelvis.
    const defaultFrame = compact ? null : defaultFramingParts(atlas, sex);
    const defaultFrameSet = defaultFrame ? new Set(defaultFrame) : null;
    const frame3 = (idx: number[], fromDefaultDirection: boolean, instant = false) => {
      const useAll = idx.length === 0;
      const boxes: T.Box3[] = [];
      parts.forEach((p, i) => {
        if (p.system === 'integumentary') return;
        if (useAll ? (defaultFrameSet ? defaultFrameSet.has(i) : wanted.has(i)) : idx.includes(i)) boxes.push(bounds[i]);
      });
      const dir = fromDefaultDirection || userMoved === false ? undefined : camera.position.clone().sub(controls.target);
      const goal = computeGoalPose(
        boxes,
        useAll,
        latest.current.inset,
        { width: el.clientWidth, height: el.clientHeight, aspect: camera.aspect, fov: FOV },
        dir,
      );
      if (!goal) return;
      const dist = goal.dist;
      goalTarget.copy(goal.target);
      goalPos.copy(goal.position);
      controls.maxDistance = Math.max(30, dist * 3);
      if (instant || reducedMotion()) {
        controls.target.copy(goalTarget);
        camera.position.copy(goalPos);
        controls.update();
        tweening = false;
      } else tweening = true;
      dirty = true;
    };

    let pendingGoal: { pose: PoseSnapshot; key: string; created: number; until: number | null } | null = null;
    const applyGoal = (p: PoseSnapshot) => {
      goalTarget.copy(p.target);
      goalPos.copy(p.position);
      userMoved = true;
      if (reducedMotion()) {
        controls.target.copy(goalTarget);
        camera.position.copy(goalPos);
        controls.update();
        tweening = false;
      } else tweening = true;
      dirty = true;
    };
    if (props.cameraApiRef) {
      props.cameraApiRef.current = {
        getGoal: () => ({ target: goalTarget.clone(), position: goalPos.clone() }),
        setGoal: (p) => {
          goalTarget.copy(p.target);
          goalPos.copy(p.position);
          userMoved = true;
          if (reducedMotion()) {
            controls.target.copy(goalTarget);
            camera.position.copy(goalPos);
            controls.update();
            tweening = false;
          } else tweening = true;
          dirty = true;
        },
        restoreGoal: (p, highlight) => {
          pendingGoal = { pose: { target: p.target.clone(), position: p.position.clone() }, key: highlight.join(','), created: performance.now(), until: null };
        },
        hasMoved: () => userMoved,
      };
    }

    // ---- state application ----
    let hasSelection = false;
    let appliedReset = latest.current.resetNonce ?? 0;
    let appliedHighlight = '';
    let appliedInset = '';
    const applyState = () => {
      const s = latest.current;
      const sel = new Set(partIdxRef.current);
      hasSelection = [...sel].some((i) => loadedParts.has(i));
      const vis = new Set<SystemId>(s.visibleSystems ?? SYSTEMS.filter((x) => x.id !== 'integumentary' && x.id !== 'pregnancy').map((x) => x.id));
      const isolate = !!s.isolate && hasSelection;
      for (let i = 0; i < n; i++) {
        const selected = sel.has(i);
        const loaded = loadedParts.has(i);
        const visible = loaded && (isolate ? selected : compact ? true : vis.has(parts[i].system) || selected);
        stateData[i * 4] = visible ? 255 : 0;
        stateData[i * 4 + 1] = selected && hasSelection ? 255 : 0;
        // Context ghosting skips superficial layers (muscle, fascia, vessels) that would just fog the view.
        stateData[i * 4 + 2] = hasSelection && !isolate && !selected && !NO_GHOST.has(parts[i].system) ? 255 : 0;
        if (hasSelection && !isolate && !selected && NO_GHOST.has(parts[i].system)) stateData[i * 4] = 0;
        stateData[i * 4 + 3] = 255;
      }
      stateTexture.needsUpdate = true;
      const wantGhost = hasSelection && !isolate && !compact;
      ghostMeshes.forEach((m) => (m.visible = wantGhost));
      dirty = true;
    };

    // ---- sizing ----
    const resize = () => {
      const w = el.clientWidth;
      const h = el.clientHeight;
      if (!w || !h) return;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, w < 768 || h < 600 ? 1.5 : 2));
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
      applyInset();
      frame3(partIdxRef.current, false, true);
      dirty = true;
    };
    const observer = new ResizeObserver(resize);
    observer.observe(el);

    // ---- picking ----
    const raycaster = new T.Raycaster();
    const pointer = new T.Vector2();
    const tap = new PointerTap();
    const hitPoint = new T.Vector3();
    const hover = document.createElement('div');
    hover.setAttribute('role', 'tooltip');
    hover.hidden = true;
    hover.className =
      'pointer-events-none absolute z-10 max-w-[240px] rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs font-medium text-ink shadow-pop';
    el.appendChild(hover);

    const pick = (clientX: number, clientY: number): number => {
      const rect = canvas.getBoundingClientRect();
      pointer.set(((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
      raycaster.setFromCamera(pointer, camera);
      let bestSolid = Infinity;
      let bestGhost = Infinity;
      let solidIdx = -1;
      let ghostIdx = -1;
      const sel = new Set(partIdxRef.current);
      for (let i = 0; i < n; i++) {
        const mesh = pickers[i];
        if (!mesh || stateData[i * 4] < 128) continue;
        if (!raycaster.ray.intersectBox(bounds[i], hitPoint)) continue;
        const hits = raycaster.intersectObject(mesh, false);
        if (!hits[0]) continue;
        const isGhost = stateData[i * 4 + 2] > 128 && !sel.has(i);
        if (isGhost) {
          if (hits[0].distance < bestGhost) {
            bestGhost = hits[0].distance;
            ghostIdx = i;
          }
        } else if (hits[0].distance < bestSolid) {
          bestSolid = hits[0].distance;
          solidIdx = i;
        }
      }
      return solidIdx >= 0 ? solidIdx : ghostIdx;
    };

    let hoverQueued = false;
    let hoverEvent: PointerEvent | null = null;
    const onDown = (e: PointerEvent) => {
      hover.hidden = true;
      tap.down(e.pointerId, e.clientX, e.clientY, e.pointerType === 'touch' ? 12 : 5);
    };
    const onMove = (e: PointerEvent) => {
      tap.move(e.pointerId, e.clientX, e.clientY);
      if (compact || e.buttons || e.pointerType === 'touch' || !latest.current.onSelect) {
        hover.hidden = true;
        return;
      }
      hoverEvent = e;
      if (hoverQueued) return;
      hoverQueued = true;
      setTimeout(() => {
        hoverQueued = false;
        const ev = hoverEvent;
        if (!ev || disposed) return;
        const i = pick(ev.clientX, ev.clientY);
        const rect = el.getBoundingClientRect();
        hover.hidden = i < 0;
        canvas.style.cursor = i < 0 ? 'grab' : 'pointer';
        if (i >= 0) {
          hover.textContent = parts[i].name;
          hover.style.left = `${Math.max(8, Math.min(ev.clientX - rect.left + 14, el.clientWidth - 250))}px`;
          hover.style.top = `${Math.max(8, Math.min(ev.clientY - rect.top + 18, el.clientHeight - 40))}px`;
        }
      }, 50);
    };
    const onUp = (e: PointerEvent) => {
      const isTap = tap.up(e.pointerId, e.clientX, e.clientY);
      if (!isTap || !latest.current.onSelect) return;
      const i = pick(e.clientX, e.clientY);
      if (i < 0) return;
      hover.hidden = true;
      latest.current.onSelect({ fmaId: parts[i].conceptId, name: parts[i].name, partId: parts[i].id });
    };
    const onCancel = (e: PointerEvent) => tap.cancel(e.pointerId);
    const onLeave = () => (hover.hidden = true);
    canvas.addEventListener('pointerdown', onDown);
    canvas.addEventListener('pointermove', onMove);
    canvas.addEventListener('pointerup', onUp);
    canvas.addEventListener('pointercancel', onCancel);
    canvas.addEventListener('pointerleave', onLeave);
    const onLost = (e: Event) => {
      e.preventDefault();
      fail('The 3D session was paused by your device. Reload to continue.');
    };
    canvas.addEventListener('webglcontextlost', onLost);

    // ---- render loop (paused while off-screen) ----
    let onScreen = true;
    const io = new IntersectionObserver((entries) => {
      onScreen = entries[entries.length - 1].isIntersecting;
      if (onScreen) dirty = true;
    });
    io.observe(el);
    const clock = new T.Clock();
    const animate = () => {
      if (disposed) return;
      frame = requestAnimationFrame(animate);
      if (!onScreen) return;
      const dt = Math.min(clock.getDelta(), 0.05);
      const s = latest.current;

      const hKey = partIdxRef.current.join(',');
      const key2 = `${hKey}|${s.isolate ? 1 : 0}|${(s.visibleSystems ?? []).join(',')}|${loadedParts.size}`;
      if (key2 !== stateKey) {
        stateKey = key2;
        applyState();
        if (hKey !== appliedHighlight) {
          appliedHighlight = hKey;
          userMoved = false;
          frame3(partIdxRef.current, true);
        }
      }
      const insetKey = `${s.inset?.right ?? 0}x${s.inset?.bottom ?? 0}`;
      if (insetKey !== appliedInset) {
        appliedInset = insetKey;
        applyInset();
        frame3(partIdxRef.current, false);
      }
      if ((s.resetNonce ?? 0) !== appliedReset) {
        appliedReset = s.resetNonce ?? 0;
        userMoved = false;
        // Reset frames the whole visible body, never the current selection (PRD 4.4 fix step 3).
        frame3([], true);
      }
      // Undo: once the restored selection is in the scene, hold the previous pose for a short settle window so the
      // selection framing and the panel inset (which can land a few frames later) do not overwrite it.
      if (pendingGoal) {
        const now = performance.now();
        if ((s.highlight ?? []).join(',') === pendingGoal.key) {
          if (pendingGoal.until === null) pendingGoal.until = now + 700;
          applyGoal(pendingGoal.pose);
          if (now >= pendingGoal.until) pendingGoal = null;
        } else if (now - pendingGoal.created > 3000) pendingGoal = null;
      }
      if (tweening) {
        const k = 1 - Math.exp(-7 * dt);
        controls.target.lerp(goalTarget, k);
        camera.position.lerp(goalPos, k);
        if (controls.target.distanceTo(goalTarget) < 0.002 && camera.position.distanceTo(goalPos) < 0.004) tweening = false;
        dirty = true;
      }
      const rotate = !!s.autoRotate && !reducedMotion() && !tweening;
      controls.autoRotate = rotate;
      controls.autoRotateSpeed = 0.9;
      controls.update();
      if (rotate) dirty = true;
      if (dirty) {
        renderer.render(scene, camera);
        dirty = false;
      }
    };
    resize();
    animate();

    return () => {
      disposed = true;
      abort.abort();
      if (props.cameraApiRef) props.cameraApiRef.current = null;
      cancelAnimationFrame(frame);
      observer.disconnect();
      io.disconnect();
      canvas.removeEventListener('pointerdown', onDown);
      canvas.removeEventListener('pointermove', onMove);
      canvas.removeEventListener('pointerup', onUp);
      canvas.removeEventListener('pointercancel', onCancel);
      canvas.removeEventListener('pointerleave', onLeave);
      canvas.removeEventListener('webglcontextlost', onLost);
      controls.dispose();
      geometries.forEach((g) => g.dispose());
      solid.forEach((m) => m.dispose());
      ghost.forEach((m) => m.dispose());
      pickMaterial.dispose();
      stateTexture.dispose();
      envTarget.dispose();
      hover.remove();
      renderer.dispose();
      renderer.forceContextLoss();
      canvas.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [atlas, compact, sceneKey]);

  const failed = error || (status === 'error' ? loadError : '');
  const loading = !failed && (!atlas || !ready);

  return (
    <div className={cn('relative h-full w-full overflow-hidden', className)}>
      <div ref={host} className="absolute inset-0" />
      {loading && !props.hideLoading && (
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <div className="flex w-56 flex-col items-center gap-3 rounded-2xl border border-border bg-surface/90 px-5 py-4 text-center shadow-card backdrop-blur">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface2" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
              <div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${Math.max(6, progress)}%` }} />
            </div>
            <span className="label-mono">{atlas ? (progress ? `Loading anatomy ${progress}%` : 'Loading anatomy') : 'Preparing atlas'}</span>
          </div>
        </div>
      )}
      {failed && (
        <div className="absolute inset-0 grid place-items-center p-6">
          <div className="flex max-w-sm flex-col items-center gap-2 text-center">
            <AlertTriangle className="h-6 w-6 text-warn" aria-hidden />
            <p className="text-sm text-muted">{failed}</p>
          </div>
        </div>
      )}
    </div>
  );
}
