import * as THREE from 'three';
import { ScrollEngine } from './engine';
import { clamp, easeInOut, easeOut, kf, lerp, ramp, smooth } from './math';
import { BOOK_COLORS, SUB_COLORS, bookColor } from './palette';
import { ACTOR_FRAG, ACTOR_VERT, BEAM_FRAG, BEAM_VERT, POINTS_FRAG, POINTS_VERT, SHELL_FRAG, SHELL_VERT, SHIELD_FRAG, SHIELD_VERT } from './shaders';
import type { StoryData } from './data';
import { loadChiasm } from './chiasm';

const FOV = 40;
const RING_Z = 1.0;
const MAX_ACTORS = 64;
const N_CH = 10;

export interface ControllerOpts {
  canvas: HTMLCanvasElement;
  root: HTMLElement; // contains [data-*] hooks
  stage: HTMLElement; // fixed stage (canvas parent)
  data: StoryData;
  dark: boolean;
  mobile: boolean;
  reduced: boolean;
  onActive: (k: number) => void;
  onFatal: (e: unknown) => void;
}

const hex3 = (h: string) => {
  const n = parseInt(h.slice(1), 16);
  return new THREE.Vector3((n >> 16) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255);
};
const cssRgb = (name: string): THREE.Vector3 => {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim().split(/\s+/).map(Number);
  return new THREE.Vector3((v[0] || 0) / 255, (v[1] || 0) / 255, (v[2] || 0) / 255);
};
const bump = (x: number, c: number, w: number) => Math.exp(-(((x - c) / w) ** 2));

type El = HTMLElement & { __k?: string };
function put(el: El | null, x: number, y: number, o: number) {
  if (!el) return;
  if (o < 0.01) {
    if (el.__k !== 'h') { el.style.opacity = '0'; el.style.visibility = 'hidden'; el.__k = 'h'; }
    return;
  }
  const k = `${Math.round(x)},${Math.round(y)},${o.toFixed(2)}`;
  if (el.__k === k) return;
  el.__k = k;
  el.style.visibility = 'visible';
  el.style.opacity = o.toFixed(2);
  el.style.transform = `translate3d(${x.toFixed(1)}px,${y.toFixed(1)}px,0)`;
}
function fade(el: El | null, o: number, dy = 0) {
  if (!el) return;
  const k = `${o.toFixed(2)},${dy.toFixed(0)}`;
  if (el.__k === k) return;
  el.__k = k;
  el.style.opacity = o.toFixed(2);
  el.style.visibility = o < 0.01 ? 'hidden' : 'visible';
  el.style.transform = dy ? `translate3d(0,${dy}px,0)` : '';
  el.style.pointerEvents = o < 0.5 ? 'none' : '';
}

interface Actor { x: number; y: number; z: number; r: number; g: number; b: number; size: number; a: number }

export class StoryController {
  private o: ControllerOpts;
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 50);
  private world = new THREE.Group();
  private pointsMat: THREE.ShaderMaterial;
  private actorMat: THREE.ShaderMaterial;
  private actorGeo = new THREE.BufferGeometry();
  private actorPos = new Float32Array(MAX_ACTORS * 3);
  private actorCol = new Float32Array(MAX_ACTORS * 3);
  private actorSize = new Float32Array(MAX_ACTORS);
  private actorAlpha = new Float32Array(MAX_ACTORS);
  private actors: Actor[] = [];
  private beamMat: THREE.ShaderMaterial;
  private beams: THREE.LineSegments;
  private floorLines: THREE.LineSegments;
  private floorMat: THREE.ShaderMaterial;
  private shell: THREE.Mesh;
  private shellMat: THREE.ShaderMaterial;
  private shield: THREE.Group;
  private shieldMat: THREE.ShaderMaterial;
  private ringMat: THREE.MeshBasicMaterial;
  private lights: THREE.Light[] = [];
  private atlas: THREE.Group | null = null;
  private atlasState: 'idle' | 'loading' | 'ready' | 'error' = 'idle';
  private engine: ScrollEngine;
  private dark: boolean;
  private raf = 0;
  private last = 0;
  private time = 0;
  private auto = 0.6;
  private s = -1;
  private sT = 0;
  private activeK = -1;
  private visible = true;
  private io: IntersectionObserver;
  private ro: ResizeObserver;
  private w = 1;
  private h = 1;
  private dead = false;
  private lostHandler: (e: Event) => void;

  // scene geometry (local/world-group space)
  private Q0 = new THREE.Vector3(0.05, 0.12, 0.45);
  private subT: THREE.Vector3[] = [];
  private subTop: THREE.Vector3[] = []; // top-hit neighbour position per sub
  private subTopSim: number[] = [];
  private decl: { pos: THREE.Vector3; start: THREE.Vector3; R: number } | null = null;
  private camKeys: { s: number; p: THREE.Vector3; t: THREE.Vector3 }[] = [];
  private evOrigin: THREE.Vector3[] = [];
  private queryCurve: THREE.CatmullRomCurve3;

  // dom hooks
  private $: (sel: string) => El | null;
  private panels: (El | null)[] = [];
  private legend: (El | null)[] = [];
  private bookLabels: (El | null)[] = [];
  private subChips: (El | null)[] = [];
  private bestChips: (El | null)[] = [];
  private cards: (El | null)[] = [];
  private cardDots: (El | null)[] = [];
  private blocks: El[] = [];
  private citeChips: { el: HTMLElement; n: number; path: SVGPathElement; block: number }[] = [];
  private tmp = new THREE.Vector3();
  private tmp2 = new THREE.Vector3();
  private cardLocal: THREE.Vector3[] = [];
  private focusW = new Float32Array(7);

  constructor(o: ControllerOpts) {
    this.o = o;
    this.dark = o.dark;
    const { canvas, data } = o;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: 'high-performance' });
    const dpr = Math.min(window.devicePixelRatio || 1, o.mobile ? 1.5 : 2);
    this.renderer.setPixelRatio(dpr);
    this.$ = (sel) => o.root.querySelector<El>(sel);

    // ---- points (one object; uniforms drive everything) ----
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(data.galaxy, 3));
    geo.setAttribute('aCluster', new THREE.BufferAttribute(data.cluster, 3));
    geo.setAttribute('aBook', new THREE.BufferAttribute(data.book, 1));
    geo.setAttribute('aSeed', new THREE.BufferAttribute(data.seed, 1));
    geo.setAttribute('aMask', new THREE.BufferAttribute(data.mask, 4));
    geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 3);
    this.pointsMat = new THREE.ShaderMaterial({
      vertexShader: POINTS_VERT,
      fragmentShader: POINTS_FRAG,
      transparent: true,
      depthWrite: false,
      depthTest: false,
      uniforms: {
        uMix: { value: 0 }, uTime: { value: 0 }, uPx: { value: 1000 }, uSize: { value: o.mobile ? 0.011 : 0.0085 },
        uDim: { value: 1 }, uFocusAmt: { value: 0 }, uSearch: { value: 0 }, uDecl: { value: 0 }, uHideEv: { value: 0 },
        uFade: { value: 1 }, uDrift: { value: o.reduced ? 0 : 1 }, uMinPx: { value: 1.6 * dpr }, uLight: { value: 0 }, uGain: { value: 0.3 },
        uFocusW: { value: this.focusW }, uPal: { value: Array.from({ length: 7 }, () => new THREE.Vector3()) },
        uGrey: { value: new THREE.Vector3() },
      },
    });
    const points = new THREE.Points(geo, this.pointsMat);
    points.frustumCulled = false;
    points.renderOrder = 1;
    this.world.add(points);

    // ---- actors ----
    this.actorGeo.setAttribute('position', new THREE.BufferAttribute(this.actorPos, 3).setUsage(THREE.DynamicDrawUsage));
    this.actorGeo.setAttribute('aCol', new THREE.BufferAttribute(this.actorCol, 3).setUsage(THREE.DynamicDrawUsage));
    this.actorGeo.setAttribute('aSize', new THREE.BufferAttribute(this.actorSize, 1).setUsage(THREE.DynamicDrawUsage));
    this.actorGeo.setAttribute('aAlpha', new THREE.BufferAttribute(this.actorAlpha, 1).setUsage(THREE.DynamicDrawUsage));
    this.actorGeo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 10);
    this.actorMat = new THREE.ShaderMaterial({
      vertexShader: ACTOR_VERT, fragmentShader: ACTOR_FRAG, transparent: true, depthWrite: false, depthTest: false,
      uniforms: { uPx: { value: 1000 }, uMinPx: { value: 1 }, uLight: { value: 0 } },
    });
    const actorPts = new THREE.Points(this.actorGeo, this.actorMat);
    actorPts.frustumCulled = false;
    actorPts.renderOrder = 5;
    this.world.add(actorPts);

    // ---- derived journey geometry ----
    const g = data.galaxyAll;
    const gp = (i: number) => new THREE.Vector3(g[i * 3], g[i * 3 + 1], g[i * 3 + 2]);
    const journey = data.story.journey;
    const near = journey?.near ?? [];
    data.subs.forEach((_, k) => {
      const nb = near[Math.min(k, near.length - 1)]?.neighbours ?? [];
      if (!nb.length) { this.subT.push(new THREE.Vector3(-0.3 + k * 0.5, 0.2, -0.2)); this.subTop.push(new THREE.Vector3()); this.subTopSim.push(0); return; }
      const c = new THREE.Vector3();
      nb.forEach((x) => c.add(gp(x.i)));
      c.multiplyScalar(1 / nb.length);
      const out = c.clone().normalize().multiplyScalar(0.32);
      this.subT.push(c.add(out));
      const top = nb.reduce((a, b) => (b.sim > a.sim ? b : a), nb[0]);
      this.subTop.push(gp(top.i));
      this.subTopSim.push(top.sim);
    });
    const dn = data.story.declined?.neighbours ?? [];
    if (dn.length) {
      const c = new THREE.Vector3();
      dn.forEach((x) => c.add(gp(x.i)));
      c.multiplyScalar(1 / dn.length);
      const dir = c.lengthSq() > 0.01 ? c.clone().normalize() : new THREE.Vector3(0.7, 0.4, 0.6).normalize();
      const pos = c.clone().add(dir.multiplyScalar(0.35));
      let mean = 0;
      dn.forEach((x) => (mean += gp(x.i).distanceTo(pos)));
      mean /= dn.length;
      this.decl = { pos, start: pos.clone().add(new THREE.Vector3(1.3, 1.0, 1.5)), R: mean * 0.55 };
    }
    this.evOrigin = (journey?.evidence ?? []).map((e) => gp(e.i));
    this.queryCurve = new THREE.CatmullRomCurve3([new THREE.Vector3(-2.1, 0.95, 2.3), new THREE.Vector3(0, 0.05, RING_Z), this.Q0.clone()], false, 'catmullrom', 0.5);

    // ---- beams ----
    const mkLines = (srcs: THREE.Vector3[], targets: THREE.Vector3[][], cols: THREE.Vector3[]) => {
      const pos: number[] = [], t: number[] = [], d: number[] = [], c: number[] = [];
      srcs.forEach((s0, k) => targets[k].forEach((tp, m) => {
        pos.push(s0.x, s0.y, s0.z, tp.x, tp.y, tp.z);
        t.push(0, 1);
        const dl = ((m * 37) % 20) / 20;
        d.push(dl, dl);
        c.push(cols[k].x, cols[k].y, cols[k].z, cols[k].x, cols[k].y, cols[k].z);
      }));
      const bg = new THREE.BufferGeometry();
      bg.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      bg.setAttribute('aT', new THREE.Float32BufferAttribute(t, 1));
      bg.setAttribute('aDelay', new THREE.Float32BufferAttribute(d, 1));
      bg.setAttribute('aCol', new THREE.Float32BufferAttribute(c, 3));
      bg.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 10);
      return bg;
    };
    const subNb = this.subT.map((_, k) => (near[Math.min(k, near.length - 1)]?.neighbours ?? []).map((x) => gp(x.i)));
    this.beamMat = new THREE.ShaderMaterial({ vertexShader: BEAM_VERT, fragmentShader: BEAM_FRAG, transparent: true, depthWrite: false, depthTest: false, uniforms: { uDraw: { value: 0 }, uAlpha: { value: 0.6 } } });
    this.beams = new THREE.LineSegments(mkLines(this.subT, subNb, this.subT.map(() => new THREE.Vector3(1, 1, 1))), this.beamMat);
    this.beams.frustumCulled = false; this.beams.renderOrder = 3;
    this.world.add(this.beams);
    this.floorMat = new THREE.ShaderMaterial({ vertexShader: BEAM_VERT, fragmentShader: BEAM_FRAG, transparent: true, depthWrite: false, depthTest: false, uniforms: { uDraw: { value: 0 }, uAlpha: { value: 0.4 } } });
    this.floorLines = new THREE.LineSegments(
      this.decl ? mkLines([this.decl.pos], [dn.map((x) => gp(x.i))], [new THREE.Vector3(0.6, 0.6, 0.6)]) : new THREE.BufferGeometry(),
      this.floorMat,
    );
    this.floorLines.frustumCulled = false; this.floorLines.renderOrder = 3;
    this.world.add(this.floorLines);

    // ---- cut-off shell ----
    this.shellMat = new THREE.ShaderMaterial({ vertexShader: SHELL_VERT, fragmentShader: SHELL_FRAG, transparent: true, depthWrite: false, depthTest: false, side: THREE.DoubleSide, uniforms: { uCol: { value: new THREE.Vector3(1, 1, 1) }, uAlpha: { value: 0 } } });
    this.shell = new THREE.Mesh(new THREE.SphereGeometry(1, 40, 28), this.shellMat);
    this.shell.visible = false; this.shell.renderOrder = 2;
    this.world.add(this.shell);

    // ---- shield ring ----
    this.shield = new THREE.Group();
    this.shieldMat = new THREE.ShaderMaterial({
      vertexShader: SHIELD_VERT, fragmentShader: SHIELD_FRAG, transparent: true, depthWrite: false, depthTest: false, side: THREE.DoubleSide,
      uniforms: { uCol: { value: new THREE.Vector3() }, uBad: { value: new THREE.Vector3() }, uAlpha: { value: 0 }, uPass: { value: 0 }, uHitT: { value: -1 }, uHit: { value: new THREE.Vector2() }, uTime: { value: 0 } },
    });
    const disc = new THREE.Mesh(new THREE.CircleGeometry(1, 64), this.shieldMat);
    this.ringMat = new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false, depthTest: false });
    const torus = new THREE.Mesh(new THREE.TorusGeometry(1, 0.014, 12, 96), this.ringMat);
    this.shield.add(disc, torus);
    this.shield.scale.setScalar(0.5);
    this.shield.position.set(0, 0.02, RING_Z);
    this.shield.visible = false; this.shield.renderOrder = 4;
    this.world.add(this.shield);

    this.scene.add(this.world);
    const amb = new THREE.AmbientLight(0xffffff, 0.7);
    const dl = new THREE.DirectionalLight(0xffffff, 2.2); dl.position.set(2, 3, 4);
    const rim = new THREE.DirectionalLight(0xaad8ff, 1.2); rim.position.set(-3, -1, -2);
    this.scene.add(amb, dl, rim); this.lights = [amb, dl, rim];

    // ---- camera path ----
    const C = this.subT.length ? this.subT.reduce((a, b) => a.clone().add(b)).multiplyScalar(1 / this.subT.length) : new THREE.Vector3();
    const D = this.decl ? this.decl.pos.clone().multiplyScalar(0.5) : new THREE.Vector3();
    const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
    const m = o.mobile ? 1.12 : 1;
    this.camKeys = [
      { s: 0, p: V(0, 0.1, 4.2 * m), t: V(0, 0, 0) },
      { s: 1, p: V(0, 0.1, 3.9 * m), t: V(0, 0, 0) },
      { s: 1.45, p: V(0, 0.15, 4.6 * m), t: V(0, 0, 0) },
      { s: 2, p: V(0, 0.15, 4.6 * m), t: V(0, 0, 0) },
      { s: 2.5, p: V(0, 0.1, 3.9 * m), t: V(0, 0, 0) },
      { s: 4, p: V(0, 0.1, 3.9 * m), t: V(0, 0, 0) },
      { s: 4.9, p: C.clone().add(V(0.3, 0.1, 2.6 * m)), t: C.clone() },
      { s: 5.05, p: C.clone().add(V(0.3, 0.1, 2.6 * m)), t: C.clone() },
      { s: 5.6, p: D.clone().add(V(0, 0.2, 3.6 * m)), t: D.clone() },
      { s: 6.05, p: D.clone().add(V(0, 0.2, 3.6 * m)), t: D.clone() },
      { s: 6.6, p: V(0, 0.1, 3.8 * m), t: V(0, 0, 0) },
      { s: 8, p: V(0, 0.1, 3.8 * m), t: V(0, 0, 0) },
      { s: 8.6, p: V(0, 0, 3.5 * m), t: V(0, 0, 0) },
      { s: 9.05, p: V(0, 0, 3.5 * m), t: V(0, 0, 0) },
      { s: 9.8, p: V(0, 0.1, 4.4 * m), t: V(0, 0, 0) },
    ];

    // ---- dom ----
    for (let k = 0; k < N_CH; k++) this.panels.push(this.$(`[data-panel="${k}"]`));
    for (let i = 0; i < 7; i++) { this.legend.push(this.$(`[data-legend="${i}"]`)); this.bookLabels.push(this.$(`[data-booklabel="${i}"]`)); }
    data.subs.forEach((_, k) => { this.subChips.push(this.$(`[data-chip="sub-${k}"]`)); this.bestChips.push(this.$(`[data-chip="best-${k}"]`)); });
    (journey?.evidence ?? []).forEach(() => this.cardLocal.push(new THREE.Vector3()));
    this.bindAnswer();

    this.engine = new ScrollEngine(
      Array.from({ length: N_CH }, (_, k) => o.root.querySelector<HTMLElement>(`[data-section="${k}"]`)!),
      o.stage,
    );

    if (process.env.NODE_ENV !== 'production') (window as unknown as Record<string, unknown>).__story = this;
    this.setTheme(o.dark);
    this.resize();
    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(o.stage);
    this.io = new IntersectionObserver((e) => { this.visible = e[0]?.isIntersecting ?? true; }, { threshold: 0 });
    this.io.observe(o.root);
    this.lostHandler = (e) => { e.preventDefault(); o.onFatal(new Error('webgl context lost')); };
    canvas.addEventListener('webglcontextlost', this.lostHandler);
    this.sT = this.engine.target();
    this.s = this.o.reduced ? this.quant(this.sT) : this.sT;
  }

  /** (Re)bind the answer's blocks and [n] chips; safe to call again if React replaced the markup. */
  private bindAnswer() {
    const o = this.o;
    this.citeChips.forEach((c) => c.path.remove());
    this.citeChips = [];
    this.cards = []; this.cardDots = [];
    (o.data.story.journey?.evidence ?? []).forEach((_, j) => { this.cards.push(this.$(`[data-card="${j}"]`)); this.cardDots.push(this.$(`[data-card-dot="${j}"]`)); });
    this.blocks = Array.from(o.root.querySelectorAll<El>('[data-answer] .md > p, [data-answer] .md li'));
    const svg = this.$('[data-lines]') as unknown as SVGElement | null;
    o.root.querySelectorAll<HTMLElement>('[data-answer] .cite-chip').forEach((el) => {
      const n = Number(el.dataset.cite);
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('pathLength', '1');
      path.setAttribute('fill', 'none');
      path.setAttribute('class', 'st-line');
      svg?.appendChild(path);
      const blk = this.blocks.findIndex((b) => b.contains(el));
      this.citeChips.push({ el, n, path, block: blk });
    });
  }

  private quant(sT: number) {
    return Math.min(9, Math.floor(sT + 1e-6)) + 1;
  }

  start() {
    this.last = performance.now();
    const loop = (now: number) => {
      if (this.dead) return;
      this.raf = requestAnimationFrame(loop);
      const dt = Math.min(0.1, (now - this.last) / 1000);
      this.last = now;
      if (!this.visible || document.hidden) return;
      try { this.frame(dt); } catch (e) { this.dead = true; cancelAnimationFrame(this.raf); this.o.onFatal(e); }
    };
    this.raf = requestAnimationFrame(loop);
  }

  jump(k: number) {
    const p = k === 0 ? 0 : k === 9 ? 0.4 : 0.16;
    this.engine.scrollTo(k, p, !this.o.reduced);
  }

  setTheme(dark: boolean) {
    this.dark = dark;
    const books = this.o.data.story.books;
    const pal = this.pointsMat.uniforms.uPal.value as THREE.Vector3[];
    for (let i = 0; i < 7; i++) {
      const b = books[i];
      pal[i].copy(hex3(b ? bookColor(b.id, i, dark) : '#888888'));
    }
    const bg = cssRgb('--c-bg');
    const accent = cssRgb('--c-accent');
    const bad = cssRgb('--c-bad');
    const muted = cssRgb('--c-muted');
    (this.pointsMat.uniforms.uGrey.value as THREE.Vector3).copy(dark ? hex3('#8a96a0') : hex3('#7b868e'));
    const blend = dark ? THREE.AdditiveBlending : THREE.NormalBlending;
    for (const m of [this.pointsMat, this.actorMat, this.beamMat, this.floorMat, this.shellMat, this.shieldMat]) { m.blending = blend; m.needsUpdate = true; }
    this.ringMat.blending = blend; this.ringMat.needsUpdate = true;
    const L = dark ? 0 : 1;
    this.pointsMat.uniforms.uLight.value = L;
    this.pointsMat.uniforms.uGain.value = dark ? 0.85 : 1;
    this.actorMat.uniforms.uLight.value = L;
    this.shieldMat.uniforms.uCol.value.copy(accent);
    this.shieldMat.uniforms.uBad.value.copy(bad);
    this.shellMat.uniforms.uCol.value.copy(dark ? hex3('#9fb2b8') : muted);
    this.ringMat.color.setRGB(accent.x, accent.y, accent.z, THREE.SRGBColorSpace);
    // beams carry per-sub colour
    const subCols = (dark ? SUB_COLORS.dark : SUB_COLORS.light).map(hex3);
    const ca = this.beams.geometry.getAttribute('aCol') as THREE.BufferAttribute | undefined;
    if (ca) {
      const per = (this.beams.geometry.getAttribute('position').count) / Math.max(1, this.subT.length);
      for (let v = 0; v < ca.count; v++) { const c = subCols[Math.floor(v / per) % subCols.length]; ca.setXYZ(v, c.x, c.y, c.z); }
      ca.needsUpdate = true;
    }
    const fa = this.floorLines.geometry.getAttribute('aCol') as THREE.BufferAttribute | undefined;
    if (fa) { const c = dark ? hex3('#9aa6ad') : hex3('#5b666d'); for (let v = 0; v < fa.count; v++) fa.setXYZ(v, c.x, c.y, c.z); fa.needsUpdate = true; }
    this.beamMat.uniforms.uAlpha.value = dark ? 0.7 : 0.8;
    // clear colour from the theme token (sRGB in, converted for the canvas by three)
    this.renderer.setClearColor(new THREE.Color().setRGB(bg.x, bg.y, bg.z, THREE.SRGBColorSpace), 1);
    this.themeAccent = accent;
    this.themeBad = bad;
    this.resize();
  }
  private themeAccent = new THREE.Vector3();
  private themeBad = new THREE.Vector3();

  resize() {
    const r = this.o.stage.getBoundingClientRect();
    this.w = Math.max(1, Math.round(r.width));
    this.h = Math.max(1, Math.round(r.height));
    this.renderer.setSize(this.w, this.h, false);
    this.camera.aspect = this.w / this.h;
    const portrait = this.w < 700 || this.h > this.w;
    // shift the scene away from the narration column
    if (portrait) this.camera.setViewOffset(this.w, this.h, 0, this.h * 0.16, this.w, this.h);
    else this.camera.setViewOffset(this.w, this.h, -this.w * 0.14, 0, this.w, this.h);
    this.camera.updateProjectionMatrix();
    const px = this.renderer.getDrawingBufferSize(new THREE.Vector2()).y / (2 * Math.tan((FOV * Math.PI) / 360));
    this.pointsMat.uniforms.uPx.value = px;
    this.actorMat.uniforms.uPx.value = px;
    // portrait: wider scene needs more distance; handled by camera keys scale
    this.camAspectBoost = portrait ? Math.max(1, 0.82 / this.camera.aspect) : 1;
    this.engine?.measure();
  }
  private camAspectBoost = 1;

  destroy() {
    this.dead = true;
    cancelAnimationFrame(this.raf);
    this.io.disconnect(); this.ro.disconnect();
    this.o.canvas.removeEventListener('webglcontextlost', this.lostHandler);
    this.citeChips.forEach((c) => c.path.remove());
    this.scene.traverse((ob) => {
      const m = ob as THREE.Mesh;
      m.geometry?.dispose?.();
      const mat = m.material as THREE.Material | THREE.Material[] | undefined;
      (Array.isArray(mat) ? mat : mat ? [mat] : []).forEach((x) => x.dispose());
    });
    this.renderer.dispose();
  }

  // ---------------------------------------------------------------- helpers
  private proj(v: THREE.Vector3, out: { x: number; y: number; d: number }) {
    this.tmp2.copy(v).applyMatrix4(this.world.matrixWorld);
    out.d = this.tmp2.distanceTo(this.camera.position);
    this.tmp2.project(this.camera);
    out.x = (this.tmp2.x * 0.5 + 0.5) * this.w;
    out.y = (-this.tmp2.y * 0.5 + 0.5) * this.h;
  }
  private screenToLocal(px: number, py: number, depth: number, out: THREE.Vector3) {
    out.set((px / this.w) * 2 - 1, -((py / this.h) * 2 - 1), 0.5).applyMatrix4(this.camera.projectionMatrixInverse);
    out.multiplyScalar(depth / -out.z).applyMatrix4(this.camera.matrixWorld);
    this.world.updateMatrixWorld();
    out.applyMatrix4(this.tmp3.copy(this.world.matrixWorld).invert());
  }
  private tmp3 = new THREE.Matrix4();
  private pj = { x: 0, y: 0, d: 0 };

  private push(p: THREE.Vector3, col: THREE.Vector3, size: number, a: number) {
    if (a < 0.004 || this.actors.length >= MAX_ACTORS) return;
    this.actors.push({ x: p.x, y: p.y, z: p.z, r: col.x, g: col.y, b: col.z, size: size * 1.8, a });
  }

  // ---------------------------------------------------------------- frame
  private frame(dt: number) {
    const reduced = this.o.reduced;
    this.time += dt;
    this.sT = this.engine.target();
    const idx = Math.min(N_CH - 1, Math.floor(this.sT + 1e-6));
    if (idx !== this.activeK) { this.activeK = idx; this.o.onActive(idx); }
    const goal = reduced ? this.quant(this.sT) : this.sT;
    if (reduced) this.s = goal;
    else {
      const d = goal - this.s;
      this.s = Math.abs(d) < 1e-4 ? goal : this.s + d * (1 - Math.exp(-dt * 9));
    }
    const s = this.s;
    const dark = this.dark;

    // atlas preload
    if (s > 6.6 && this.atlasState === 'idle') this.loadAtlas();

    // ---- camera & world ----
    const keys = this.camKeys;
    let i = 0;
    while (i < keys.length - 2 && s > keys[i + 1].s) i++;
    const a = keys[i], b = keys[i + 1];
    const t = smooth(s, a.s, b.s);
    const boost = this.camAspectBoost;
    this.camera.position.lerpVectors(a.p, b.p, t);
    if (boost !== 1) this.camera.position.sub(this.tmp.lerpVectors(a.t, b.t, t)).multiplyScalar(boost).add(this.tmp);
    this.tmp.lerpVectors(a.t, b.t, t);
    this.camera.lookAt(this.tmp);
    this.camera.updateMatrixWorld();

    const aw = 1 - smooth(s, 1.8, 2.3) + smooth(s, 9.1, 9.6);
    if (!reduced) this.auto += dt * 0.045 * (1 - smooth(s, 1.8, 2.3));
    const wrapped = ((this.auto + Math.PI) % (2 * Math.PI)) - Math.PI;
    this.world.rotation.y = reduced ? 0.5 * Math.min(1, aw) : (wrapped + 0.45 * Math.min(s, 2)) * clamp(aw);
    this.world.rotation.x = 0.2 * (1 - smooth(s, 1, 2.3)) * (1 - smooth(s, 8.5, 9));
    this.world.updateMatrixWorld();

    // ---- point uniforms ----
    const U = this.pointsMat.uniforms;
    U.uTime.value = reduced ? 0 : this.time;
    U.uMix.value = smooth(s, 1.0, 1.45) * (1 - smooth(s, 2.0, 2.4));
    const pb = s - 1;
    const segW = 0.66 / 7;
    const fAmt = reduced ? 0 : smooth(pb, 0.2, 0.3) * (1 - smooth(pb, 0.97, 1.0));
    let act = -1, best = 0.4;
    for (let k = 0; k < 7; k++) {
      const c = 0.3 + (k + 0.5) * segW;
      const w = 1 - smooth(Math.abs(pb - c), segW * 0.42, segW * 0.78);
      this.focusW[k] = w;
      if (w > best && fAmt > 0.5) { best = w; act = k; }
    }
    U.uFocusAmt.value = fAmt;
    U.uDim.value = kf(s, [[0, 1], [2.0, 1], [2.4, 0.34], [4.0, 0.34], [4.3, 0.2], [5.0, 0.2], [5.3, 0.26], [6.0, 0.26], [6.3, 0.16], [8.0, 0.16], [9.0, 0.5], [10, 0.55]]);
    U.uSearch.value = smooth(s, 4.05, 4.45) * (1 - smooth(s, 5.0, 5.3));
    U.uDecl.value = smooth(s, 5.3, 5.6) * (1 - smooth(s, 6.0, 6.3));
    U.uHideEv.value = smooth(s, 5.97, 6.03);
    U.uFade.value = clamp(1 - smooth(s, 8.0, 8.4) + smooth(s, 9.05, 9.45));
    this.shieldMat.uniforms.uTime.value = this.time;

    // legend / book labels
    const books = this.o.data.story.books;
    for (let k = 0; k < 7; k++) {
      const el = this.legend[k];
      if (el) { const on = act === k ? '1' : '0'; if (el.dataset.on !== on) el.dataset.on = on; }
      const lb = this.bookLabels[k];
      if (lb && books[k]) {
        const mix = U.uMix.value as number;
        const c0 = books[k].galaxy_centroid, c1 = books[k].centroid;
        this.tmp.set(lerp(c0[0], c1[0], mix), lerp(c0[1], c1[1], mix), lerp(c0[2], c1[2], mix));
        this.proj(this.tmp, this.pj);
        const depth = clamp((this.pj.d - (this.camera.position.length() - 1.3)) / 2.6);
        const vis = smooth(mix, 0.9, 1) * (1 - smooth(s, 2.0, 2.2));
        const focus = fAmt > 0.01 ? lerp(0.35, 1, this.focusW[k]) : 1;
        put(lb, this.pj.x, this.pj.y, vis * focus * (1 - 0.55 * depth));
      }
    }

    // ---- actors ----
    this.actors.length = 0;
    const acc = this.themeAccent;
    const subCols = (dark ? SUB_COLORS.dark : SUB_COLORS.light).map(hex3);
    const white = dark ? new THREE.Vector3(1, 1, 1) : new THREE.Vector3(0.06, 0.18, 0.22);
    const pj = this.pj;

    // query & refusal (guard)
    const guardP = s - 2;
    const uq = easeInOut(ramp(guardP, 0.06, 0.5));
    const qAlpha = ramp(s, 2.02, 2.12) * (1 - ramp(s, 3.05, 3.22));
    const qPos = this.queryCurve.getPoint(clamp(uq));
    if (qAlpha > 0.004) {
      for (let tr = 5; tr >= 1; tr--) {
        const ut = uq - tr * 0.035;
        if (ut > 0 && uq < 0.999) this.push(this.queryCurve.getPoint(ut), acc, 0.05 * (1 - tr * 0.15), qAlpha * 0.28 * (1 - tr * 0.17));
      }
      this.push(qPos, white, 0.085, qAlpha);
    }
    const ur = ramp(s, 2.5, 2.9);
    const hitP = new THREE.Vector3(0.1, -0.08, RING_Z + 0.015);
    const RS = new THREE.Vector3(1.95, -0.65, 2.1), RB = new THREE.Vector3(1.75, -0.95, 1.55);
    const refPos = (u: number) => (u < 0.5 ? new THREE.Vector3().lerpVectors(RS, hitP, easeInOut(u * 2) ** 1.2) : new THREE.Vector3().lerpVectors(hitP, RB, easeOut((u - 0.5) * 2)).add(new THREE.Vector3(0, 0.12 * Math.sin((u - 0.5) * 2 * Math.PI), 0)));
    const rAlpha = ramp(s, 2.48, 2.56) * (1 - ramp(s, 3.2, 3.5));
    const rPos = refPos(ur);
    const bad = this.themeBad;
    if (rAlpha > 0.004) {
      for (let tr = 4; tr >= 1; tr--) { const ut = ur - tr * 0.04; if (ut > 0 && ur < 0.999) this.push(refPos(ut), bad, 0.05 * (1 - tr * 0.15), rAlpha * 0.28 * (1 - tr * 0.2)); }
      this.push(rPos, bad, 0.08, rAlpha);
    }
    // shield
    const shAlpha = smooth(s, 2.1, 2.35) * (1 - smooth(s, 3.3, 3.7));
    this.shield.visible = shAlpha > 0.004;
    if (this.shield.visible) {
      const su = this.shieldMat.uniforms;
      su.uAlpha.value = shAlpha * (dark ? 1 : 1.4);
      su.uPass.value = bump(uq, 0.5, 0.07) * smooth(s, 2.1, 2.4);
      const ht = (s - 2.7) / 0.55;
      su.uHitT.value = s > 2.7 && ht < 1.2 ? ht : -1;
      (su.uHit.value as THREE.Vector2).set(0.16, -0.18);
      this.ringMat.opacity = shAlpha * (0.8 + 0.2 * Math.sin(this.time * 2));
    }

    // sub-questions (route/search)
    const subAlpha = ramp(s, 3.04, 3.2) * (1 - ramp(s, 5.2, 5.5));
    const split = easeInOut(ramp(s - 3, 0.1, 0.75));
    const subP: THREE.Vector3[] = [];
    this.subT.forEach((T, k) => {
      const lat = Math.sin(Math.PI * split) * 0.18 * (k % 2 ? 1 : -1);
      const p = new THREE.Vector3().lerpVectors(this.Q0, T, split).add(new THREE.Vector3(lat, Math.sin(Math.PI * split) * 0.1, 0));
      subP.push(p);
      const c = subCols[k % subCols.length];
      const pulse = 1 + 0.12 * Math.sin(this.time * 3 + k) * (reduced ? 0 : 1);
      this.push(p, c, 0.065 * pulse, subAlpha);
    });
    // beams
    const bDraw = easeInOut(ramp(s, 4.12, 4.65));
    this.beamMat.uniforms.uDraw.value = bDraw;
    this.beams.visible = bDraw > 0.001 && s < 5.6;
    const bFade = 1 - smooth(s, 5.05, 5.4);
    this.beamMat.uniforms.uAlpha.value = (dark ? 0.7 : 0.85) * bFade;

    // declined
    const dk = this.decl;
    const dAlpha = ramp(s, 5.15, 5.3) * (1 - ramp(s, 6.0, 6.3));
    let dPos = this.tmp3v;
    if (dk) {
      const u = easeInOut(ramp(s, 5.15, 5.6));
      dPos = new THREE.Vector3().lerpVectors(dk.start, dk.pos, u);
      this.push(dPos, bad, 0.075, dAlpha);
      const sh = easeOut(ramp(s, 5.55, 5.9));
      this.shell.visible = sh > 0.01 && dAlpha > 0.004;
      this.shell.position.copy(dk.pos);
      this.shell.scale.setScalar(Math.max(0.001, dk.R * sh));
      this.shellMat.uniforms.uAlpha.value = sh * (1 - ramp(s, 6.0, 6.3)) * (dark ? 1 : 1.6);
      this.floorMat.uniforms.uDraw.value = easeInOut(ramp(s, 5.65, 5.95));
      this.floorMat.uniforms.uAlpha.value = 0.55 * (1 - ramp(s, 6.0, 6.3));
      this.floorLines.visible = s > 5.6 && s < 6.35;
    }

    // evidence: need card positions (DOM reads first)
    const evs = this.o.data.story.journey?.evidence ?? [];
    const evOn = s > 5.9 && s < 8.3;
    if (evOn) {
      const sr = this.o.stage.getBoundingClientRect();
      const depth = this.camera.position.distanceTo(this.tmp.set(0, 0, 0));
      for (let j = 0; j < evs.length; j++) {
        const dEl = this.cardDots[j];
        if (!dEl) continue;
        const r = dEl.getBoundingClientRect();
        this.screenToLocal(r.left + r.width / 2 - sr.left, r.top + r.height / 2 - sr.top, depth, this.cardLocal[j]);
      }
    }
    const cit = ramp(s, 7.45, 7.75);
    const evEnd = 1 - ramp(s, 8.02, 8.25);
    evs.forEach((e, j) => {
      const org = this.evOrigin[j];
      if (!org) return;
      const tj = easeInOut(ramp(s, 6.12 + 0.07 * j, 6.62 + 0.07 * j));
      const p = new THREE.Vector3().lerpVectors(org, this.cardLocal[j], tj);
      p.z += Math.sin(Math.PI * tj) * 0.45;
      const bi = Math.max(0, books.findIndex((x) => x.id === e.book));
      const col = hex3(bookColor(e.book, bi, dark));
      const grey = dark ? hex3('#8a96a0') : hex3('#6b767d');
      const mixC = e.cited ? 0 : cit;
      const c = new THREE.Vector3().lerpVectors(col, grey, mixC);
      const size = 0.065 * (1 + (e.cited ? 0.7 * cit : 0)) * (1 + 0.5 * bump(s, 6.05, 0.04));
      const al = ramp(s, 5.98, 6.08) * (1 - mixC * 0.5) * evEnd * (s > 4.2 ? 1 : 0);
      this.push(p, c, size, al);
    });

    // flush actors
    const n = this.actors.length;
    for (let k = 0; k < n; k++) {
      const A = this.actors[k];
      this.actorPos[k * 3] = A.x; this.actorPos[k * 3 + 1] = A.y; this.actorPos[k * 3 + 2] = A.z;
      this.actorCol[k * 3] = A.r; this.actorCol[k * 3 + 1] = A.g; this.actorCol[k * 3 + 2] = A.b;
      this.actorSize[k] = A.size; this.actorAlpha[k] = A.a;
    }
    this.actorGeo.setDrawRange(0, n);
    for (const nm of ['position', 'aCol', 'aSize', 'aAlpha']) (this.actorGeo.getAttribute(nm) as THREE.BufferAttribute).needsUpdate = true;

    // ---- atlas mesh ----
    const atlasA = smooth(s, 8.2, 8.6) * (1 - smooth(s, 9.05, 9.4));
    if (this.atlas) {
      const mat = this.atlas.userData.material as THREE.MeshStandardMaterial;
      mat.opacity = atlasA;
      this.atlas.visible = atlasA > 0.003;
      this.atlas.rotation.y = reduced ? 0.6 : this.time * 0.45 + 0.4;
      this.atlas.rotation.x = 0.25;
      const sc = lerp(0.8, 1, atlasA);
      this.atlas.scale.setScalar(sc);
    }

    // ---- DOM overlays ----
    this.updateDom(s, idx, subP, rPos, qPos, dPos, atlasA, qAlpha, rAlpha, dAlpha, evs.length);

    // ---- render ----
    this.renderer.render(this.scene, this.camera);
  }
  private tmp3v = new THREE.Vector3();

  private updateDom(s: number, idx: number, subP: THREE.Vector3[], rPos: THREE.Vector3, qPos: THREE.Vector3, dPos: THREE.Vector3, atlasA: number, qAlpha: number, rAlpha: number, dAlpha: number, nEv: number) {
    const reduced = this.o.reduced;
    const pj = this.pj;
    if ((this.blocks[0] && !this.blocks[0].isConnected) || (this.cardDots[0] && !this.cardDots[0].isConnected)) this.bindAnswer();
    // panels
    for (let k = 0; k < N_CH; k++) {
      const p = s - k;
      let o: number;
      if (reduced) o = k === idx ? 1 : 0;
      else o = (k === 0 ? 1 : ramp(p, 0.0, 0.1)) * (k === N_CH - 1 ? 1 : 1 - ramp(p, 0.9, 1.0));
      const dy = reduced ? 0 : (1 - (k === 0 ? 1 : ramp(p, 0, 0.1))) * 16 - ramp(p, 0.9, 1) * 10;
      fade(this.panels[k], o, Math.round(dy));
    }
    // hero cue
    fade(this.$('[data-cue]'), 1 - smooth(s, 0.0, 0.25));

    // query chip
    this.proj(qPos, pj);
    put(this.$('[data-chip="query"]'), pj.x, pj.y, qAlpha * ramp(s, 2.1, 2.25));
    this.proj(rPos, pj);
    put(this.$('[data-chip="refuse"]'), pj.x, pj.y, rAlpha * ramp(s, 2.62, 2.74));
    put(this.$('[data-tag="refuse"]'), pj.x, pj.y, rAlpha * ramp(s, 2.74, 2.86));

    // sub chips: label always, text during the route chapter
    const subA = ramp(s, 3.04, 3.2) * (1 - ramp(s, 5.2, 5.5));
    subP.forEach((p, k) => {
      this.proj(p, pj);
      const el = this.subChips[k];
      put(el, pj.x, pj.y, subA * ramp(s, 3.15, 3.3));
      if (el) { const tx = ramp(s, 3.3, 3.45) * (1 - ramp(s, 4.0, 4.15)); const t = el.querySelector<HTMLElement>('[data-text]'); if (t && t.dataset.v !== tx.toFixed(1)) { t.dataset.v = tx.toFixed(1); t.style.opacity = tx.toFixed(2); t.style.maxHeight = tx > 0.05 ? '6rem' : '0px'; } }
      const tp = this.subTop[k];
      if (tp && this.bestChips[k]) {
        this.proj(tp, pj);
        put(this.bestChips[k], pj.x, pj.y, ramp(s, 4.62, 4.78) * (1 - ramp(s, 5.08, 5.28)));
      }
    });

    // declined
    if (this.decl) {
      this.proj(dPos, pj);
      put(this.$('[data-chip="declined"]'), pj.x, pj.y, dAlpha * ramp(s, 5.6, 5.8));
    } else put(this.$('[data-chip="declined"]'), 0, 0, 0);

    // cards
    const cardEnd = 1 - ramp(s, 8.02, 8.25);
    const unc = ramp(s, 7.65, 7.85);
    for (let j = 0; j < nEv; j++) {
      const tj = easeInOut(ramp(s, 6.12 + 0.07 * j, 6.62 + 0.07 * j));
      const el = this.cards[j];
      if (!el) continue;
      const o = ramp(tj, 0.55, 1) * cardEnd;
      fade(el, o, Math.round((1 - ramp(tj, 0.55, 1)) * 10));
      const cited = el.dataset.cited === '1';
      const st = cited ? (ramp(s, 7.45, 7.75) > 0.5 ? 'cited' : '') : unc > 0.5 ? 'uncited' : ramp(s, 7.45, 7.75) > 0.5 ? 'dim' : '';
      if (el.dataset.state !== st) el.dataset.state = st;
    }
    fade(this.$('[data-cards-wrap]'), 1);

    // answer card + lines
    const aA = ramp(s, 7.0, 7.14) * cardEnd;
    fade(this.$('[data-answer]'), aA, Math.round((1 - ramp(s, 7.0, 7.14)) * 14));
    const nb = this.blocks.length;
    const revealed: number[] = [];
    this.blocks.forEach((b, k) => {
      const r0 = 7.12 + (0.5 * k) / Math.max(1, nb);
      const r = ramp(s, r0, r0 + 0.08);
      revealed[k] = r;
      const key = r.toFixed(1);
      if (b.dataset.r !== key) { b.dataset.r = key; b.style.opacity = (0.08 + 0.92 * r).toFixed(2); b.style.transform = `translate3d(0,${((1 - r) * 8).toFixed(1)}px,0)`; }
    });
    const linesOn = aA > 0.05 && s > 7.1 && !this.o.mobile;
    if (linesOn) {
      const sr = this.o.stage.getBoundingClientRect();
      const ar = this.$('[data-answer]')!.getBoundingClientRect();
      const reads = this.citeChips.map((c) => {
        const r = c.el.getBoundingClientRect();
        const ev = this.o.data.story.journey.evidence;
        const j = ev.findIndex((e) => e.n === c.n);
        const d = j >= 0 ? this.cardDots[j]?.getBoundingClientRect() : null;
        return { r, d, j };
      });
      this.citeChips.forEach((c, k) => {
        const { r, d } = reads[k];
        const inView = r.top > ar.top + 6 && r.bottom < ar.bottom - 6;
        const rv = revealed[c.block] ?? 1;
        if (!d || !inView || rv < 0.5) { if (c.path.dataset.on !== '0') { c.path.dataset.on = '0'; c.path.style.opacity = '0'; } return; }
        const x1 = r.right - sr.left, y1 = r.top + r.height / 2 - sr.top;
        const x2 = d.left + d.width / 2 - sr.left, y2 = d.top + d.height / 2 - sr.top;
        const dx = Math.max(40, (x2 - x1) * 0.5);
        c.path.setAttribute('d', `M${x1.toFixed(1)},${y1.toFixed(1)} C${(x1 + dx).toFixed(1)},${y1.toFixed(1)} ${(x2 - dx).toFixed(1)},${y2.toFixed(1)} ${x2.toFixed(1)},${y2.toFixed(1)}`);
        const draw = ramp(s, 7.3 + 0.03 * k, 7.55 + 0.03 * k);
        c.path.style.strokeDashoffset = String(1 - draw);
        const cited = this.o.data.story.journey.evidence[reads[k].j]?.cited;
        c.path.style.opacity = String((cited ? 0.85 : 0.35) * cardEnd * rv);
        c.path.dataset.on = '1';
      });
    } else this.citeChips.forEach((c) => { if (c.path.dataset.on !== '0') { c.path.dataset.on = '0'; c.path.style.opacity = '0'; } });

    // atlas
    const win = smooth(s, 8.15, 8.5) * (1 - smooth(s, 9.05, 9.4));
    const ready = this.atlasState === 'ready';
    fade(this.$('[data-atlas-still]'), ready ? 0 : win);
    fade(this.$('[data-atlas-tag]'), win);
    void atlasA;
  }

  private loadAtlas() {
    this.atlasState = 'loading';
    loadChiasm()
      .then((g) => {
        if (this.dead) return;
        this.atlas = g;
        g.visible = false;
        this.scene.add(g);
        this.atlasState = 'ready';
        this.o.root.dataset.atlas = 'ready';
      })
      .catch(() => { this.atlasState = 'error'; this.o.root.dataset.atlas = 'error'; });
  }
}
void BOOK_COLORS;
