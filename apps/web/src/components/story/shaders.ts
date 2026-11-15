export const POINTS_VERT = /* glsl */ `
attribute vec3 aCluster;
attribute float aBook;
attribute float aSeed;
attribute vec4 aMask; // x search neighbour, y evidence, z declined neighbour, w cited evidence
uniform float uMix, uTime, uPx, uSize, uDim, uFocusAmt, uSearch, uDecl, uHideEv, uFade, uDrift, uMinPx;
uniform float uFocusW[7];
uniform vec3 uPal[7];
uniform vec3 uGrey;
varying vec3 vCol;
varying float vA;
void main() {
  vec3 p = mix(position, aCluster, uMix);
  float ph = aSeed * 6.2831;
  p += 0.014 * uDrift * vec3(sin(uTime * 0.25 + ph), cos(uTime * 0.21 + ph * 1.3), sin(uTime * 0.19 + ph * 0.7));
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  int bi = int(aBook + 0.5);
  vec3 col = uPal[bi];
  float fw = uFocusW[bi];
  float b = uDim;
  b = mix(b, mix(0.16, 1.35, fw), uFocusAmt);
  b = mix(b, mix(0.10, 1.9, aMask.x), uSearch);
  float dn = aMask.z * uDecl;
  b = mix(b, max(b, 1.5), dn);
  col = mix(col, uGrey, dn);
  float hide = 1.0 - uHideEv * aMask.y;
  float grow = 1.0 + 0.8 * aMask.x * uSearch + 0.7 * fw * uFocusAmt + 1.3 * dn;
  float tw = 1.0 + 0.22 * sin(uTime * 1.6 + aSeed * 60.0);
  float s = uSize * (0.55 + 0.9 * aSeed * aSeed) * grow * tw * hide * mix(1.0, 0.6, uMix);
  gl_PointSize = clamp(s * uPx / max(0.1, -mv.z), uMinPx * step(0.001, hide), 28.0);
  gl_Position = projectionMatrix * mv;
  vCol = col;
  vA = clamp(b, 0.0, 2.2) * uFade * hide * mix(1.0, 0.6, uMix);
}`;

export const POINTS_FRAG = /* glsl */ `
uniform float uLight;
uniform float uGain;
varying vec3 vCol;
varying float vA;
void main() {
  vec2 c = gl_PointCoord - 0.5;
  float d = length(c) * 2.0;
  if (d > 1.0 || vA < 0.004) discard;
  float core = smoothstep(1.0, 0.0, d);
  float a = core * core * vA * uGain;
  if (uLight > 0.5) {
    gl_FragColor = vec4(vCol, clamp(a * 1.5, 0.0, 1.0));
  } else {
    gl_FragColor = vec4(vCol * (0.75 + 0.9 * pow(core, 3.0)), a);
  }
}`;

export const ACTOR_VERT = /* glsl */ `
attribute vec3 aCol;
attribute float aSize;
attribute float aAlpha;
uniform float uPx, uMinPx;
varying vec3 vCol;
varying float vA;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_PointSize = clamp(aSize * uPx / max(0.1, -mv.z), 0.0, 120.0) * step(0.003, aAlpha);
  gl_Position = projectionMatrix * mv;
  vCol = aCol;
  vA = aAlpha;
}`;

export const ACTOR_FRAG = /* glsl */ `
uniform float uLight;
varying vec3 vCol;
varying float vA;
void main() {
  vec2 c = gl_PointCoord - 0.5;
  float d = length(c) * 2.0;
  if (d > 1.0) discard;
  float core = smoothstep(0.34, 0.0, d);
  float halo = pow(smoothstep(1.0, 0.0, d), 2.4);
  float ring = smoothstep(0.08, 0.0, abs(d - 0.62)) * 0.35;
  float a = clamp(core + halo * 0.55 + ring, 0.0, 1.0) * vA;
  if (uLight > 0.5) gl_FragColor = vec4(vCol, a);
  else gl_FragColor = vec4(mix(vCol, vec3(1.0), core * 0.6), a);
}`;

export const BEAM_VERT = /* glsl */ `
attribute float aT;
attribute float aDelay;
attribute vec3 aCol;
varying float vT;
varying float vD;
varying vec3 vCol;
void main() {
  vT = aT; vD = aDelay; vCol = aCol;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;

export const BEAM_FRAG = /* glsl */ `
uniform float uDraw, uAlpha;
varying float vT;
varying float vD;
varying vec3 vCol;
void main() {
  float local = clamp((uDraw - vD * 0.5) / 0.5, 0.0, 1.0);
  if (vT > local) discard;
  float head = exp(-(local - vT) * 7.0);
  gl_FragColor = vec4(vCol, uAlpha * (0.45 + 0.55 * head));
}`;

export const SHELL_VERT = /* glsl */ `
varying vec3 vN;
varying vec3 vV;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vN = normalize(normalMatrix * normal);
  vV = normalize(-mv.xyz);
  gl_Position = projectionMatrix * mv;
}`;
export const SHELL_FRAG = /* glsl */ `
uniform vec3 uCol; uniform float uAlpha;
varying vec3 vN; varying vec3 vV;
void main() {
  float f = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.2);
  gl_FragColor = vec4(uCol, (0.05 + 0.6 * f) * uAlpha);
}`;

export const SHIELD_VERT = /* glsl */ `
varying vec2 vUv;
void main() { vUv = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
export const SHIELD_FRAG = /* glsl */ `
uniform vec3 uCol; uniform vec3 uBad; uniform float uAlpha, uPass, uHitT, uTime; uniform vec2 uHit;
varying vec2 vUv;
void main() {
  float r = length(vUv);
  float edge = smoothstep(0.55, 1.0, r);
  float a = 0.035 + 0.25 * edge + 0.10 * sin(r * 26.0 - uTime * 0.8) * edge;
  a += uPass * (1.0 - r) * 0.5;
  float rip = 0.0;
  if (uHitT >= 0.0) {
    float dr = length(vUv - uHit);
    float w = uHitT * 1.5;
    rip = exp(-pow((dr - w) * 9.0, 2.0)) * (1.0 - clamp(uHitT, 0.0, 1.0));
    a += rip * 0.9;
  }
  vec3 col = mix(uCol, uBad, clamp(rip * 1.4, 0.0, 1.0));
  if (r > 1.0) discard;
  gl_FragColor = vec4(col, clamp(a, 0.0, 1.0) * uAlpha);
}`;
