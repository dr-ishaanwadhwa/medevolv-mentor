import * as THREE from 'three';
import { ScrollEngine } from '../story/engine';
import { clamp, easeInOut, easeOut, lerp, ramp } from '../story/math';
import { bookColor } from '../story/palette';
import { ACTOR_FRAG, ACTOR_VERT, POINTS_FRAG, POINTS_VERT } from '../story/shaders';
import type { StoryData } from '../story/data';
import { parseChiasm } from './chiasm-bin';
import { reducedSceneState, sceneState, type SceneState } from './gate';

/** The landing's WebGL layer: the real library map (story/library.bin) settling into seven book galaxies, the cited
 * books glowing, the decline dimming everything, and the optic chiasm (public/landing/chiasm.bin) for scene 3.
 * Reuses the /how shaders, palette, maths and scroll engine as they are; never touches controller.ts.
 * Loaded with a dynamic import after first paint, so three.js is not in the landing's initial JS (L-5). */

const FOV = 40;
const CAM_D = 3.9;

export interface LandingSceneOpts {
  canvas: HTMLCanvasElement;
  stage: HTMLElement;
  sections: HTMLElement[];
  /** absolutely positioned label elements, one per story.json book, in book order */
  labels: (HTMLElement | null)[];
  data: StoryData;
  dark: boolean;
  mobile: boolean;
  reduced: boolean;
  heroBooks: number[];
  whyBooks: number[];
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

export class LandingScene {
  private o: LandingSceneOpts;
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 50);
  private world = new THREE.Group();
  private pointsMat: THREE.ShaderMaterial;
  private actorMat: THREE.ShaderMaterial;
  private actorGeo = new THREE.BufferGeometry();
  private actorPos = new Float32Array(3);
  private actorCol = new Float32Array(3);
  private actorSize = new Float32Array(1);
  private actorAlpha = new Float32Array(1);
  private focusW = new Float32Array(7);
  private heroW = new Float32Array(7);
  private whyW = new Float32Array(7);
  private engine: ScrollEngine;
  private chiasm: THREE.Group | null = null;
  private chiasmState: 'idle' | 'loading' | 'ready' | 'error' = 'idle';
  private chiasmMat: THREE.MeshPhysicalMaterial | null = null;
  private rim = { value: new THREE.Color('#8fe3ee') };
  private lights: THREE.Light[] = [];
  private accent = new THREE.Vector3();
  private dark: boolean;
  private raf = 0;
  private last = 0;
  private time = 0;
  private t0 = -1;
  private cur: SceneState = sceneState(0);
  private w = 1;
  private h = 1;
  private dead = false;
  private visible = true;
  private io: IntersectionObserver;
  private ro: ResizeObserver;
  private tmp = new THREE.Vector3();
  private lostHandler: (e: Event) => void;

  constructor(o: LandingSceneOpts) {
    this.o = o;
    this.dark = o.dark;
    const { canvas, data } = o;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: 'high-performance' });
    // pixel ratio cap 1.5 on phones (PRD smoothness tuning)
    const dpr = Math.min(window.devicePixelRatio || 1, o.mobile ? 1.5 : 2);
    this.renderer.setPixelRatio(dpr);

    // spread each book's cluster around its centroid, as /how does, so each book reads as its own galaxy
    const bk = data.story.books;
    for (let k = 0; k < data.count; k++) {
      const ct = bk[data.book[k]]?.centroid;
      if (!ct) continue;
      for (let a = 0; a < 3; a++) data.cluster[k * 3 + a] = ct[a] + (data.cluster[k * 3 + a] - ct[a]) * 2.1;
    }
    for (const i of o.heroBooks) if (i < 7) this.heroW[i] = 1;
    for (const i of o.whyBooks) if (i < 7) this.whyW[i] = 1;

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(data.galaxy, 3));
    geo.setAttribute('aCluster', new THREE.BufferAttribute(data.cluster, 3));
    geo.setAttribute('aBook', new THREE.BufferAttribute(data.book, 1));
    geo.setAttribute('aSeed', new THREE.BufferAttribute(data.seed, 1));
    // the landing has no journey masks: every point is a plain library point
    geo.setAttribute('aMask', new THREE.BufferAttribute(new Float32Array(data.count * 4), 4));
    geo.setAttribute('aQ', new THREE.BufferAttribute(new Float32Array(data.count), 1));
    geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 3);
    this.pointsMat = new THREE.ShaderMaterial({
      vertexShader: POINTS_VERT,
      fragmentShader: POINTS_FRAG,
      transparent: true,
      depthWrite: false,
      depthTest: false,
      uniforms: {
        uMix: { value: o.reduced ? 1 : 0 }, uTime: { value: 0 }, uPx: { value: 1000 }, uSize: { value: o.mobile ? 0.011 : 0.0085 },
        uDim: { value: 1 }, uFocusAmt: { value: 0 }, uSearch: { value: 0 }, uDecl: { value: 0 }, uHideEv: { value: 0 },
        uFade: { value: o.reduced ? 1 : 0 }, uDrift: { value: o.reduced ? 0 : 1 }, uMinPx: { value: 1.6 * dpr }, uLight: { value: 0 },
        uGain: { value: 0.85 }, uFocusW: { value: this.focusW }, uPal: { value: Array.from({ length: 7 }, () => new THREE.Vector3()) },
        uGrey: { value: new THREE.Vector3() }, uFocusLo: { value: 0.3 }, uExpl: { value: 0 },
      },
    });
    const points = new THREE.Points(geo, this.pointsMat);
    points.frustumCulled = false;
    points.renderOrder = 1;
    this.world.add(points);

    // one "actor": the hero chip that lifts off and flies into its book's galaxy
    this.actorGeo.setAttribute('position', new THREE.BufferAttribute(this.actorPos, 3).setUsage(THREE.DynamicDrawUsage));
    this.actorGeo.setAttribute('aCol', new THREE.BufferAttribute(this.actorCol, 3).setUsage(THREE.DynamicDrawUsage));
    this.actorGeo.setAttribute('aSize', new THREE.BufferAttribute(this.actorSize, 1).setUsage(THREE.DynamicDrawUsage));
    this.actorGeo.setAttribute('aAlpha', new THREE.BufferAttribute(this.actorAlpha, 1).setUsage(THREE.DynamicDrawUsage));
    this.actorGeo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 10);
    this.actorMat = new THREE.ShaderMaterial({
      vertexShader: ACTOR_VERT, fragmentShader: ACTOR_FRAG, transparent: true, depthWrite: false, depthTest: false,
      uniforms: { uPx: { value: 1000 }, uMinPx: { value: 1 }, uLight: { value: 0 } },
    });
    const actor = new THREE.Points(this.actorGeo, this.actorMat);
    actor.frustumCulled = false;
    actor.renderOrder = 5;
    this.world.add(actor);

    // lights for the chiasm only
    const amb = new THREE.AmbientLight('#ffffff', 0.5);
    const key = new THREE.DirectionalLight('#ffffff', 1.6);
    key.position.set(2, 3, 4);
    const tint = new THREE.DirectionalLight('#4fb3bd', 1.1);
    tint.position.set(-3, -1, -2);
    this.lights.push(amb, key, tint);
    this.scene.add(amb, key, tint);
    this.scene.add(this.world);

    this.engine = new ScrollEngine(o.sections, o.stage);
    this.setTheme(o.dark);

    this.io = new IntersectionObserver(([e]) => { this.visible = e.isIntersecting; }, { threshold: 0 });
    this.io.observe(o.stage);
    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(o.stage);
    this.lostHandler = (e: Event) => { e.preventDefault(); this.fail(new Error('webgl context lost')); };
    canvas.addEventListener('webglcontextlost', this.lostHandler);
  }

  start() {
    this.last = performance.now();
    const loop = (now: number) => {
      if (this.dead) return;
      this.raf = requestAnimationFrame(loop);
      const dt = Math.min(0.05, (now - this.last) / 1000);
      this.last = now;
      if (!this.visible || document.hidden) return;
      try { this.frame(dt); } catch (e) { this.fail(e); }
    };
    this.raf = requestAnimationFrame(loop);
  }

  /** Scene 3 is within a viewport: fetch the pre-extracted chiasm (tens of KB). Never the atlas manifest (L-6). */
  loadChiasm() {
    if (this.chiasmState !== 'idle') return;
    this.chiasmState = 'loading';
    fetch('/landing/chiasm.bin')
      .then((r) => { if (!r.ok) throw new Error('chiasm.bin'); return r.arrayBuffer(); })
      .then((buf) => {
        if (this.dead) return;
        const mat = new THREE.MeshPhysicalMaterial({
          color: '#2a7f88', roughness: 0.34, metalness: 0.05, clearcoat: 0.9, clearcoatRoughness: 0.2,
          sheen: 0.6, sheenColor: new THREE.Color('#9fe3ec'), transparent: true, opacity: 0,
        });
        const rim = this.rim;
        // fresnel rim glow, as on /how: edges catch the accent colour so it reads as a lit specimen
        mat.onBeforeCompile = (sh) => {
          sh.uniforms.uRim = rim;
          sh.fragmentShader = 'uniform vec3 uRim;\n' + sh.fragmentShader.replace(
            '#include <opaque_fragment>',
            'float fr = pow(1.0 - clamp(dot(normalize(vViewPosition), normal), 0.0, 1.0), 2.6);\noutgoingLight += uRim * fr * 0.9;\n#include <opaque_fragment>',
          );
        };
        const g = new THREE.Group();
        for (const p of parseChiasm(buf)) {
          const geo = new THREE.BufferGeometry();
          geo.setAttribute('position', new THREE.BufferAttribute(p.positions, 3));
          geo.setAttribute('normal', new THREE.BufferAttribute(p.normals, 3, true));
          geo.setIndex(new THREE.BufferAttribute(p.indices, 1));
          g.add(new THREE.Mesh(geo, mat));
        }
        g.scale.setScalar(1.5);
        g.rotation.set(0.35, 0.6, 0);
        g.visible = false;
        this.chiasm = g;
        this.chiasmMat = mat;
        this.scene.add(g);
        this.chiasmTheme();
        this.chiasmState = 'ready';
      })
      .catch((e) => { this.chiasmState = 'error'; console.warn('[landing] chiasm failed; the text and credit stay', e); });
  }

  setTheme(dark: boolean) {
    this.dark = dark;
    const books = this.o.data.story.books;
    const pal = this.pointsMat.uniforms.uPal.value as THREE.Vector3[];
    for (let i = 0; i < 7; i++) pal[i].copy(hex3(books[i] ? bookColor(books[i].id, i, dark) : '#888888'));
    (this.pointsMat.uniforms.uGrey.value as THREE.Vector3).copy(dark ? hex3('#8a96a0') : hex3('#7b868e'));
    // palette.ts: dark uses additive glow, light uses normal blending with deeper colours
    const blend = dark ? THREE.AdditiveBlending : THREE.NormalBlending;
    for (const m of [this.pointsMat, this.actorMat]) { m.blending = blend; m.needsUpdate = true; }
    this.pointsMat.uniforms.uLight.value = dark ? 0 : 1;
    this.pointsMat.uniforms.uGain.value = dark ? 0.85 : 1;
    this.pointsMat.uniforms.uFocusLo.value = dark ? 0.3 : 0.4;
    this.actorMat.uniforms.uLight.value = dark ? 0 : 1;
    this.accent = cssRgb('--c-accent');
    const bg = cssRgb('--c-bg');
    this.renderer.setClearColor(new THREE.Color().setRGB(bg.x, bg.y, bg.z, THREE.SRGBColorSpace), 1);
    this.chiasmTheme();
    this.resize();
  }

  private chiasmTheme() {
    if (!this.chiasmMat) return;
    const a = this.accent, k = this.dark ? 0.55 : 0.8;
    this.chiasmMat.color.setRGB(a.x * k, a.y * k, a.z * k, THREE.SRGBColorSpace);
    this.rim.value.setRGB(Math.min(1, a.x * 1.5), Math.min(1, a.y * 1.5), Math.min(1, a.z * 1.5), THREE.SRGBColorSpace);
    (this.lights[2] as THREE.DirectionalLight).color.setRGB(a.x, a.y, a.z, THREE.SRGBColorSpace);
  }

  resize() {
    const r = this.o.stage.getBoundingClientRect();
    this.w = Math.max(1, Math.round(r.width));
    this.h = Math.max(1, Math.round(r.height));
    this.renderer.setSize(this.w, this.h, false);
    this.camera.aspect = this.w / this.h;
    if (this.w >= 1024) {
      // text panels sit in the left column (max-w-xl): centre the scene in the free area to their right
      const col = Math.min(this.w * 0.5, 640);
      const cx = col + (this.w - col) / 2;
      this.camera.setViewOffset(this.w, this.h, -(cx - this.w / 2), 0, this.w, this.h);
    } else {
      this.camera.clearViewOffset();
    }
    this.camera.updateProjectionMatrix();
    const px = this.renderer.getDrawingBufferSize(new THREE.Vector2()).y / (2 * Math.tan((FOV * Math.PI) / 360));
    this.pointsMat.uniforms.uPx.value = px;
    this.actorMat.uniforms.uPx.value = px;
    this.engine.measure();
  }

  private frame(dt: number) {
    const { reduced, data, mobile } = this.o;
    this.time += dt;
    if (this.t0 < 0) this.t0 = this.time;
    const intro = this.time - this.t0;
    const U = this.pointsMat.uniforms;
    U.uTime.value = this.time;

    const s = this.engine.target();
    const goal = reduced ? reducedSceneState(s) : sceneState(s);
    // reduced motion: cross-fade towards the scene's end state; otherwise follow the scroll closely
    const k = 1 - Math.exp(-dt * (reduced ? 4 : 10));
    const c = this.cur;
    (Object.keys(goal) as (keyof SceneState)[]).forEach((key) => { c[key] += (goal[key] - c[key]) * k; });

    // intro: the map fades in, then settles from the shared t-SNE map into seven book galaxies
    const fadeIn = reduced ? 1 : easeOut(ramp(intro, 0, 1.1));
    U.uMix.value = reduced ? 1 : easeInOut(ramp(intro, 0.5, 2.6));
    U.uFade.value = fadeIn * c.points;
    U.uDim.value = c.dim;
    U.uFocusAmt.value = c.focus * (reduced ? 1 : ramp(intro, 1.6, 2.6));
    for (let i = 0; i < 7; i++) this.focusW[i] = lerp(this.heroW[i], this.whyW[i], c.whyMix);

    // camera: slow drift (none when reduced), a little scroll-linked turn
    const boost = mobile || this.w < 700 ? Math.max(1, 0.82 / this.camera.aspect) : 1;
    const d = CAM_D * boost;
    this.camera.position.set(0, 0.25, d);
    this.camera.lookAt(0, mobile ? 0.25 : 0, 0);
    this.world.rotation.y = reduced ? 0.5 : 0.5 + this.time * 0.035 + 0.25 * clamp(s / 4);
    this.world.rotation.x = 0.15;

    // the chip's flight: from just in front of the camera into the first cited book's galaxy, then a soft pulse there
    const books = data.story.books;
    const target = c.whyMix > 0.5 ? this.o.whyBooks[0] : this.o.heroBooks[0];
    const bk = target !== undefined ? books[target] : undefined;
    let aA = 0;
    if (bk) {
      this.tmp.set(bk.centroid[0], bk.centroid[1], bk.centroid[2]);
      const fly = reduced ? 1 : easeInOut(ramp(intro, 0.9, 2.4));
      if (fly < 1) {
        // start point in world space: in front of the camera, low and left (where the hero chips sit)
        const start = this.world.worldToLocal(new THREE.Vector3(-0.8, -0.5, d - 1.2));
        this.tmp.lerpVectors(start, this.tmp, fly);
      }
      aA = (reduced ? 1 : ramp(intro, 0.8, 1.0)) * c.focus;
      const pulse = reduced ? 1 : 1 + 0.15 * Math.sin(this.time * 2.4);
      this.actorPos.set([this.tmp.x, this.tmp.y, this.tmp.z]);
      const col = hex3(bookColor(bk.id, target!, this.dark));
      this.actorCol.set([col.x, col.y, col.z]);
      this.actorSize[0] = (mobile ? 0.12 : 0.09) * pulse;
    }
    this.actorAlpha[0] = aA;
    for (const n of ['position', 'aCol', 'aSize', 'aAlpha']) (this.actorGeo.getAttribute(n) as THREE.BufferAttribute).needsUpdate = true;

    // chiasm
    if (this.chiasm && this.chiasmMat) {
      const a = c.chiasm;
      this.chiasm.visible = a > 0.01;
      this.chiasmMat.opacity = a;
      if (!reduced) this.chiasm.rotation.y += dt * 0.35;
      this.chiasm.position.set(0, mobile ? 0.3 : 0, 0);
    }

    this.renderer.render(this.scene, this.camera);
    this.placeLabels(c.labels * fadeIn * (reduced ? 1 : ramp(intro, 1.8, 2.6)));
  }

  private placeLabels(alpha: number) {
    const books = this.o.data.story.books;
    const mix = this.pointsMat.uniforms.uMix.value as number;
    for (let k = 0; k < this.o.labels.length; k++) {
      const el = this.o.labels[k];
      const bk = books[k];
      if (!el || !bk) continue;
      const c0 = bk.galaxy_centroid, c1 = bk.centroid;
      this.tmp.set(lerp(c0[0], c1[0], mix), lerp(c0[1], c1[1], mix), lerp(c0[2], c1[2], mix));
      this.tmp.applyMatrix4(this.world.matrixWorld).project(this.camera);
      const x = (this.tmp.x * 0.5 + 0.5) * this.w;
      const y = (-this.tmp.y * 0.5 + 0.5) * this.h - 22;
      const glow = lerp(this.heroW[k], this.whyW[k], this.cur.whyMix);
      const o = alpha * (this.cur.focus > 0.05 ? lerp(0.45, 1, glow) : 1);
      el.style.opacity = o.toFixed(2);
      el.style.visibility = o < 0.02 ? 'hidden' : 'visible';
      el.style.transform = `translate3d(${x.toFixed(1)}px,${y.toFixed(1)}px,0) translate(-50%,-50%)`;
    }
  }

  private fail(e: unknown) {
    if (this.dead) return;
    this.destroy();
    this.o.onFatal(e);
  }

  /** Idempotent: fail() destroys, and the component's unmount calls it again. */
  destroy() {
    if (this.dead) return;
    this.dead = true;
    cancelAnimationFrame(this.raf);
    this.io.disconnect();
    this.ro.disconnect();
    this.o.canvas.removeEventListener('webglcontextlost', this.lostHandler);
    this.scene.traverse((obj) => {
      const m = obj as THREE.Mesh;
      m.geometry?.dispose?.();
      const mat = m.material as THREE.Material | THREE.Material[] | undefined;
      if (Array.isArray(mat)) mat.forEach((x) => x.dispose()); else mat?.dispose?.();
    });
    this.renderer.dispose();
    // Free the WebGL context now rather than at GC: browsers cap live contexts (~16) and drop the oldest, which can be
    // the atlas or /how canvas after a few / <-> /ask round trips.
    this.renderer.forceContextLoss();
  }
}
