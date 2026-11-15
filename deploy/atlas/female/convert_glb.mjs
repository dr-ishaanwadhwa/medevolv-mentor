#!/usr/bin/env node
// Convert the HRA "3D Reference Organ Set for United, Female" v1.5 GLB into the atlas manifest layout
// the viewer reads (same Part schema as the male BodyParts3D set): float32 positions, int16 normals,
// uint32 indices, byte offsets, per-part bounds, 7 MB-ish chunk files.
//
// Zero dependencies (a GLB is a JSON chunk plus a binary chunk), so there is nothing to install.
// Run via deploy/atlas/female/build_female.sh. Output goes to the human-atlas clone's public/models as
// `female.json` + `female-src-N.bin`; scripts/optimize-anatomy.mjs (there) then welds, simplifies and
// writes `female-N.bin`, and deletes the female-src files.
//
//   node convert_glb.mjs [--glb PATH] [--out DIR] [--check-only] [--exclude-allen]
//
// Steps (PRD 4.5): 1 bounds check (fails if neither units/axes interpretation matches within 5%), 2 bake node
// transforms, 3 place the feet on the stage, 4 clean names, 5 map ids, 6 map systems, 7 write manifest.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import os from 'node:os';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const arg = (name, dflt) => {
  const i = process.argv.indexOf(name);
  return i >= 0 ? process.argv[i + 1] : dflt;
};
const GLB = arg('--glb', path.join(HERE, 'source/3d-vh-f-united.glb'));
const OUT = arg('--out', path.join(os.homedir(), 'Projects/third_party/human-atlas/public/models'));
const CHECK_ONLY = process.argv.includes('--check-only');
// The Allen brain meshes' licence is known only second hand (PRD 4.5); this ships the model without them.
const EXCLUDE_ALLEN = process.argv.includes('--exclude-allen');
const REPORT = path.join(HERE, 'work/convert_report.json');
const ID_MAP = path.join(HERE, 'id_map.csv');
const OVERRIDES = path.join(HERE, 'id_overrides.csv');

// HRA placement metadata bounding box of the full model, metres (967 x 1666 x 329 mm, PRD 4.5 / fem 3.1).
const META_EXTENT_M = [0.967, 1.666, 0.329];
const TOLERANCE = 0.05;
const CHUNK_TARGET = 7_000_000;

// ---------------------------------------------------------------- GLB reading
const buf = fs.readFileSync(GLB);
if (buf.toString('ascii', 0, 4) !== 'glTF') throw new Error('not a GLB');
const jsonLen = buf.readUInt32LE(12);
const gltf = JSON.parse(buf.toString('utf8', 20, 20 + jsonLen));
const binStart = 20 + jsonLen + 8; // chunk header is 8 bytes (length + type)
if (buf.toString('ascii', 20 + jsonLen + 4, 20 + jsonLen + 8) !== 'BIN\0') throw new Error('no BIN chunk');
if (gltf.extensionsRequired?.length) throw new Error(`unsupported required extensions: ${gltf.extensionsRequired}`);
const N = gltf.nodes;

const COMP = { 5120: [Int8Array, 1], 5121: [Uint8Array, 1], 5122: [Int16Array, 2], 5123: [Uint16Array, 2], 5125: [Uint32Array, 4], 5126: [Float32Array, 4] };
const NCOMP = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 };

/** Read an accessor into a fresh typed array (tightly packed, honouring byteStride). */
function readAccessor(ai) {
  const a = gltf.accessors[ai];
  if (a.sparse) throw new Error(`accessor ${ai}: sparse not supported`);
  const bv = gltf.bufferViews[a.bufferView];
  const [Type, size] = COMP[a.componentType];
  const n = NCOMP[a.type];
  const base = binStart + (bv.byteOffset ?? 0) + (a.byteOffset ?? 0);
  const stride = bv.byteStride ?? n * size;
  const out = new Type(a.count * n);
  if (stride === n * size) {
    // copy to guarantee alignment
    const src = buf.subarray(base, base + a.count * n * size);
    new Uint8Array(out.buffer).set(src);
  } else {
    for (let i = 0; i < a.count; i++) {
      const row = new Uint8Array(out.buffer, i * n * size, n * size);
      row.set(buf.subarray(base + i * stride, base + i * stride + n * size));
    }
  }
  return out;
}

// ---------------------------------------------------------------- transforms (baked into vertices)
const I4 = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]; // column-major
function mul(a, b) {
  const o = new Array(16).fill(0);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) for (let k = 0; k < 4; k++) o[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
  return o;
}
function local(n) {
  if (n.matrix) return n.matrix.slice();
  const [tx, ty, tz] = n.translation ?? [0, 0, 0];
  const [x, y, z, w] = n.rotation ?? [0, 0, 0, 1];
  const [sx, sy, sz] = n.scale ?? [1, 1, 1];
  const r = [
    1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0,
    2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0,
    2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0,
    0, 0, 0, 1,
  ];
  return [r[0] * sx, r[1] * sx, r[2] * sx, 0, r[4] * sy, r[5] * sy, r[6] * sy, 0, r[8] * sz, r[9] * sz, r[10] * sz, 0, tx, ty, tz, 1];
}
const parent = new Array(N.length).fill(-1);
N.forEach((n, i) => (n.children ?? []).forEach((c) => (parent[c] = i)));
const world = new Array(N.length);
const roots = gltf.scenes[gltf.scene ?? 0].nodes;
(function walk(i, p) {
  world[i] = mul(p, local(N[i]));
  (N[i].children ?? []).forEach((c) => walk(c, world[i]));
})(roots[0], I4) ;
roots.slice(1).forEach((r) => (function walk(i, p) { world[i] = mul(p, local(N[i])); (N[i].children ?? []).forEach((c) => walk(c, world[i])); })(r, I4));

const isIdentity = (m) => m.every((v, i) => Math.abs(v - I4[i]) < 1e-9);
const transformed = world.filter((m) => m && !isIdentity(m)).length;

// ---------------------------------------------------------------- read all mesh nodes
const meshNodes = [];
N.forEach((n, i) => { if (n.mesh !== undefined && !(EXCLUDE_ALLEN && n.name.startsWith('Allen_'))) meshNodes.push(i); });

const cleanTable = [
  [/\bjejenum\b/i, 'jejunum'],
  [/\beigth\b/i, 'eighth'],
  [/\bopthalmic\b/i, 'ophthalmic'],
  [/\bfibria\b/i, 'fimbria'],
  [/\bschlemms\b/i, "Schlemm's"],
];
const typoFixes = new Set();
/** Display name from a node name: drop prefix, trailing _L/_R becomes a leading Left/Right, underscores to spaces. */
function cleanName(raw) {
  let s = raw.replace(/^VH_F_/, '').replace(/^Allen_/, '');
  let side = null;
  const m = s.match(/_([LR])$/);
  if (m) { side = m[1] === 'L' ? 'Left' : 'Right'; s = s.slice(0, -2); }
  s = s.replace(/_+$/g, '').replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
  for (const [re, fix] of cleanTable) if (re.test(s)) { typoFixes.add(`${raw} -> ${fix}`); s = s.replace(re, fix); }
  s = s.replace(/([a-z])(\d+)$/i, '$1 $2');
  if (side && !/\b(left|right)\b/i.test(s)) s = `${side} ${s}`;
  return s.charAt(0).toUpperCase() + s.slice(1);
}
const slug = (raw) => raw.replace(/^VH_F_/, '').replace(/[^A-Za-z0-9]+/g, '_').replace(/^_+|_+$/g, '').toUpperCase();

// ---------------------------------------------------------------- step 1: bounds check
function applyPoint(m, x, y, z) {
  return [m[0] * x + m[4] * y + m[8] * z + m[12], m[1] * x + m[5] * y + m[9] * z + m[13], m[2] * x + m[6] * y + m[10] * z + m[14]];
}
const lo = [Infinity, Infinity, Infinity];
const hi = [-Infinity, -Infinity, -Infinity];
const skinBox = { lo: [Infinity, Infinity, Infinity], hi: [-Infinity, -Infinity, -Infinity] };
for (const ni of meshNodes) {
  const prim = gltf.meshes[N[ni].mesh].primitives[0];
  const a = gltf.accessors[prim.attributes.POSITION];
  if (!a.min || !a.max) throw new Error(`accessor of ${N[ni].name} has no min/max`);
  for (let c = 0; c < 8; c++) {
    const p = applyPoint(world[ni], c & 1 ? a.max[0] : a.min[0], c & 2 ? a.max[1] : a.min[1], c & 4 ? a.max[2] : a.min[2]);
    for (let k = 0; k < 3; k++) {
      lo[k] = Math.min(lo[k], p[k]); hi[k] = Math.max(hi[k], p[k]);
      if (N[ni].name === 'VH_F_skin') { skinBox.lo[k] = Math.min(skinBox.lo[k], p[k]); skinBox.hi[k] = Math.max(skinBox.hi[k], p[k]); }
    }
  }
}
const extent = hi.map((h, k) => h - lo[k]);
// The HRA metadata box describes the body (skin) surface. The 8 placenta/umbilical reference items are placed
// outside the skin in z, so the whole-model extent is larger in z; compare the SKIN extent and report both.
const skinExtent = skinBox.hi.map((h, k) => h - skinBox.lo[k]);
// Candidate interpretations: scale (1 = metres, 0.001 = millimetres) x up axis (Y-up expected extent order x,y,z; Z-up swaps y and z).
const candidates = [];
for (const scale of [1, 0.001]) {
  for (const up of ['Y', 'Z']) {
    const e = up === 'Y' ? skinExtent.map((v) => v * scale) : [skinExtent[0] * scale, skinExtent[2] * scale, skinExtent[1] * scale];
    const err = e.map((v, k) => Math.abs(v - META_EXTENT_M[k]) / META_EXTENT_M[k]);
    candidates.push({ scale, up, extentM: e.map((v) => +v.toFixed(4)), maxRelError: +Math.max(...err).toFixed(4), ok: Math.max(...err) <= TOLERANCE });
  }
}
const chosen = candidates.find((c) => c.ok);
console.log(`bake: ${transformed} node(s) carry a non-identity world transform; mesh nodes: ${meshNodes.length}`);
console.log(`bounds after bake: skin extent ${skinExtent.map((v) => v.toFixed(4)).join(' x ')}; whole model ${extent.map((v) => v.toFixed(4)).join(' x ')} (placenta/umbilical items lie outside the skin in z)`);
console.log(`metadata extent (m): ${META_EXTENT_M.join(' x ')}`);
candidates.forEach((c) => console.log(`  scale ${c.scale} up ${c.up}: ${c.extentM.join(' x ')} max rel err ${c.maxRelError} ${c.ok ? 'MATCH' : 'no'}`));
if (!chosen) throw new Error('bounds check failed: neither units nor up-axis interpretation matches the metadata within 5%');
if (chosen.scale !== 1 || chosen.up !== 'Y') {
  throw new Error(`bounds check chose scale ${chosen.scale}, up ${chosen.up}; this converter only implements metres / Y-up. Extend it before continuing.`);
}
console.log('bounds check: metres, Y-up (scale 1) confirmed');
// Orientation check: left structures (_L) should sit at +x like the male model, anterior (nipples) at +z.
{
  const cx = (name) => {
    const ni = N.findIndex((n) => n.name === name);
    const a = gltf.accessors[gltf.meshes[N[ni].mesh].primitives[0].attributes.POSITION];
    return [(a.min[0] + a.max[0]) / 2, (a.min[2] + a.max[2]) / 2];
  };
  const [lx] = cx('VH_F_nipple_L');
  const [rx] = cx('VH_F_nipple_R');
  const [, nz] = cx('VH_F_nipple_L');
  const zMid = (skinBox.lo[2] + skinBox.hi[2]) / 2;
  if (!(lx > 0 && rx < 0)) throw new Error('orientation check failed: left nipple is not at +x');
  if (!(nz > zMid)) throw new Error('orientation check failed: nipple is not anterior (+z)');
  console.log('orientation check: left = +x, anterior = +z (same as the male model)');
}

// ---------------------------------------------------------------- step 3: placement on the stage
// Male stage: skin spans y 0..1.73, x and z centred on 0. Do the same with the female skin box.
const shift = [-(skinBox.lo[0] + skinBox.hi[0]) / 2, -skinBox.lo[1], -(skinBox.lo[2] + skinBox.hi[2]) / 2];
console.log(`placement shift (m): ${shift.map((v) => v.toFixed(4)).join(', ')}`);
if (CHECK_ONLY) process.exit(0);

// ---------------------------------------------------------------- step 6: systems
const DIRECT = {
  VH_F_digestive_system: 'digestive',
  VH_F_urinary_system: 'urinary',
  VH_F_respiratory_system: 'respiratory',
  VH_F_lymphatic_system: 'lymphatic',
  VH_F_skeletal_system: 'skeletal',
  VH_F_muscular_system: 'muscular',
};
function systemOf(ni) {
  const chain = [];
  for (let i = ni; i >= 0; i = parent[i]) chain.unshift(N[i].name);
  const leaf = N[ni].name;
  const has = (re) => chain.some((c) => re.test(c));
  if (leaf.startsWith('Allen_')) return 'nervous';
  if (has(/^VH_F_integumentary_system$/)) return has(/mammary_gland/) ? 'reproductive_female' : 'integumentary';
  if (has(/^VH_F_reproductive_system$/)) return has(/^VH_F_placenta$/) ? 'pregnancy' : 'reproductive_female';
  if (has(/^VH_F_nervous_system$/)) return has(/^VH_F_eyes$|^VH_F_eye_[LR]$/) ? 'sensory' : 'nervous';
  if (has(/^VH_F_digestive_system$/) && has(/palatine_tonsil/)) return 'lymphatic';
  if (has(/^VH_F_circulatory_system$/)) {
    if (has(/^VH_F_heart$/)) return 'cardiac';
    const text = chain.join(' ');
    if (/vein|venous|vena|sinus/i.test(leaf)) return 'venous';
    if (/arter|aorta|trunk|arcade|arteriole/i.test(leaf)) return 'arterial';
    if (/veins_of|_vein/i.test(text) && !/arteries_of/i.test(text)) return 'venous';
    if (/arteries_of|_artery/i.test(text)) return 'arterial';
    return 'arterial';
  }
  for (const [k, v] of Object.entries(DIRECT)) if (has(new RegExp(`^${k}$`))) return v;
  return 'connective';
}

// ---------------------------------------------------------------- step 5: id mapping
const overrides = new Map(); // node name -> {concept_id, concept_name, reviewed_by}
if (fs.existsSync(OVERRIDES)) {
  for (const line of fs.readFileSync(OVERRIDES, 'utf8').split('\n').slice(1)) {
    if (!line.trim() || line.startsWith('#')) continue;
    const [mesh_name, concept_id, concept_name, reviewed_by] = line.split(',');
    overrides.set(mesh_name, { concept_id, concept_name, reviewed_by: reviewed_by ?? '' });
  }
}
/** FMA:123 -> FMA123 (our id form); UBERON:0000995 kept; anything else is not a usable ontology id. */
function ontologyId(extras) {
  const raw = (extras?.ontologyid ?? '').trim();
  let m = raw.match(/^FMA:(\d+)$/);
  if (m) return { id: `FMA${m[1]}`, kind: 'FMA' };
  m = raw.match(/^UBERON:(\d+)$/);
  if (m) return { id: `UBERON:${m[1]}`, kind: 'UBERON' };
  return { id: null, kind: raw && raw !== '-' ? 'malformed' : 'none' };
}
const validLabel = (extras) => {
  const l = (extras?.label ?? '').replace(/\s+/g, ' ').trim();
  return l && l !== '-' ? l : null;
};
const fixLabel = (l) => cleanTable.reduce((s, [re, fix]) => s.replace(re, fix), l);

// part ids must be unique and uppercase
const partIdOf = new Map();
const usedIds = new Set();
for (const ni of meshNodes) {
  let id = `VHF:${slug(N[ni].name)}`;
  for (let k = 2; usedIds.has(id); k++) id = `VHF:${slug(N[ni].name)}_${k}`;
  usedIds.add(id);
  partIdOf.set(ni, id);
}
// how many meshes share each ontology id
const shareCount = new Map();
for (const ni of meshNodes) {
  const { id } = ontologyId(N[ni].extras);
  if (id) shareCount.set(id, (shareCount.get(id) ?? 0) + 1);
}

// ---------------------------------------------------------------- geometry + manifest
fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(path.join(HERE, 'work'), { recursive: true });
for (const f of fs.readdirSync(OUT)) if (/^female-src-\d+\.bin$/.test(f)) fs.unlinkSync(path.join(OUT, f));

const parts = [];
const chunks = [];
let blob = [];
let blobBytes = 0;
let triangles = 0;
const partInfo = []; // aligned with parts: {node, mapSource}
const flush = () => {
  if (!blobBytes) return;
  const url = `/models/female-src-${chunks.length}.bin`;
  fs.writeFileSync(path.join(OUT, path.basename(url)), Buffer.concat(blob));
  chunks.push({ url, bytes: blobBytes });
  blob = []; blobBytes = 0;
};
const append = (typed) => {
  const pad = (4 - (blobBytes % 4)) % 4;
  if (pad) { blob.push(Buffer.alloc(pad)); blobBytes += pad; }
  const offset = blobBytes;
  const b = Buffer.from(typed.buffer, typed.byteOffset, typed.byteLength);
  blob.push(b); blobBytes += b.length;
  return offset;
};

for (const ni of meshNodes) {
  const node = N[ni];
  const prim = gltf.meshes[node.mesh].primitives[0];
  if (gltf.meshes[node.mesh].primitives.length !== 1) throw new Error(`${node.name}: multiple primitives`);
  if ((prim.mode ?? 4) !== 4) throw new Error(`${node.name}: not a triangle list`);
  const P = readAccessor(prim.attributes.POSITION);
  const Nrm = readAccessor(prim.attributes.NORMAL);
  const idx = Uint32Array.from(readAccessor(prim.indices));
  const vc = P.length / 3;
  if (Nrm.length !== P.length) throw new Error(`${node.name}: normals length`);
  const m = world[ni];
  const pos = new Float32Array(P.length);
  const nor = new Int16Array(P.length);
  const bmin = [Infinity, Infinity, Infinity];
  const bmax = [-Infinity, -Infinity, -Infinity];
  for (let v = 0; v < vc; v++) {
    const p = applyPoint(m, P[v * 3], P[v * 3 + 1], P[v * 3 + 2]);
    for (let k = 0; k < 3; k++) {
      pos[v * 3 + k] = p[k] + shift[k];
      bmin[k] = Math.min(bmin[k], pos[v * 3 + k]); bmax[k] = Math.max(bmax[k], pos[v * 3 + k]);
    }
    // normals: rotate by the upper 3x3 (all transforms are rigid/uniform here), renormalise
    const x = Nrm[v * 3], y = Nrm[v * 3 + 1], z = Nrm[v * 3 + 2];
    let nx = m[0] * x + m[4] * y + m[8] * z, ny = m[1] * x + m[5] * y + m[9] * z, nz = m[2] * x + m[6] * y + m[10] * z;
    const len = Math.hypot(nx, ny, nz) || 1;
    nor[v * 3] = Math.round((nx / len) * 32767); nor[v * 3 + 1] = Math.round((ny / len) * 32767); nor[v * 3 + 2] = Math.round((nz / len) * 32767);
  }
  for (const i of idx) if (i >= vc) throw new Error(`${node.name}: index out of range`);
  if (idx.length % 3 || !idx.length) throw new Error(`${node.name}: bad index count`);
  if (blobBytes > CHUNK_TARGET) flush();
  const chunk = chunks.length;
  parts.push({
    id: partIdOf.get(ni), name: cleanName(node.name), conceptId: '', system: systemOf(ni), chunk,
    positions: append(pos), normals: append(nor), indices: append(idx), vertexCount: vc, indexCount: idx.length,
    bounds: [bmin, bmax],
  });
  partInfo.push({ node: ni });
  triangles += idx.length / 3;
}
flush();

// ---------------------------------------------------------------- concepts and id_map
const conceptElements = new Map(); // id -> Set(part id)
const conceptNames = new Map();
const rows = []; // id_map.csv
const stats = { FMA: 0, UBERON: 0, 'synthetic:no-ontology-id': 0, 'synthetic:shared-id-split': 0, 'synthetic:malformed-id': 0, override: 0 };
const addConcept = (id, name, partId) => {
  if (!conceptElements.has(id)) { conceptElements.set(id, new Set()); conceptNames.set(id, name); }
  conceptElements.get(id).add(partId);
};
parts.forEach((p, k) => {
  const node = N[partInfo[k].node];
  const ov = overrides.get(node.name);
  const { id: oid, kind } = ontologyId(node.extras);
  const label = validLabel(node.extras);
  const synthetic = `HRA:VH_F_${slug(node.name)}`;
  let conceptId, conceptName, source, reviewed = '';
  if (ov) {
    conceptId = ov.concept_id; conceptName = ov.concept_name || p.name; source = 'override'; reviewed = ov.reviewed_by;
    stats.override++;
  } else if (oid && shareCount.get(oid) === 1) {
    conceptId = oid; conceptName = fixLabel(label ?? p.name); source = `hra-extras:${kind}`; stats[kind]++;
  } else if (oid) {
    // Several meshes (usually Left and Right) carry the same ontology class: each mesh keeps its own concept
    // so a click selects one side; the shared class becomes a parent concept holding all of them.
    conceptId = synthetic; conceptName = p.name; source = `synthetic:shared-id-split (${oid})`; stats['synthetic:shared-id-split']++;
    addConcept(oid, fixLabel(label ?? p.name), p.id);
  } else {
    conceptId = synthetic; conceptName = p.name;
    source = kind === 'malformed' ? `synthetic:malformed-id (${node.extras?.ontologyid})` : 'synthetic:no-ontology-id';
    stats[kind === 'malformed' ? 'synthetic:malformed-id' : 'synthetic:no-ontology-id']++;
  }
  p.conceptId = conceptId;
  addConcept(conceptId, conceptName, p.id);
  rows.push([node.name, conceptId, conceptName, source, reviewed]);
});
// Group nodes (uterus, ovary, ...) become compound concepts over all their descendant meshes.
const descendants = (i) => {
  const out = [];
  (function w(k) { if (N[k].mesh !== undefined && nodeToPart.has(k)) out.push(k); (N[k].children ?? []).forEach(w); })(i);
  return out;
};
const nodeToPart = new Map(partInfo.map((x, k) => [x.node, parts[k].id]));
let groupConcepts = 0;
N.forEach((n, i) => {
  if (!n.children?.length || i === roots[0] || n.name.startsWith('Allen_')) return;
  const els = descendants(i).map((k) => nodeToPart.get(k));
  if (!els.length) return;
  const gid = `HRA:VH_F_${slug(n.name)}`;
  const name = cleanName(n.name);
  if (n.mesh !== undefined) {
    // A mesh node with children (vagina, retina...) keeps its own concept and also owns its descendants' meshes.
    const own = parts[parts.findIndex((p) => p.id === nodeToPart.get(i))].conceptId;
    for (const e of els) addConcept(own, conceptNames.get(own), e);
    return;
  }
  for (const e of els) addConcept(gid, name, e);
  groupConcepts++;
  rows.push([n.name, gid, name, 'group', '']);
});
// Brain group: one concept for all Allen_* parts so "brain" is searchable and selectable as a whole.
{
  const els = meshNodes.filter((k) => N[k].name.startsWith('Allen_')).map((k) => nodeToPart.get(k));
  if (els.length) for (const e of els) addConcept('HRA:VH_F_ALLEN_BRAIN', 'Brain (Allen Human Brain Atlas regions)', e);
  if (els.length) rows.push([`Allen_* (${els.length} meshes)`, 'HRA:VH_F_ALLEN_BRAIN', 'Brain (Allen Human Brain Atlas regions)', 'group', '']);
}
const concepts = [...conceptElements].map(([id, set]) => ({ id, name: conceptNames.get(id), elements: [...set] }));

const manifest = {
  version: 'HRA-VH-F-united-1.5',
  sex: 'female',
  source: 'HRA VH_F united v1.5',
  scope: `Female reference organs · ${parts.length} source meshes · skeleton and muscles partial${EXCLUDE_ALLEN ? ' · brain regions not included' : ''}`,
  brain: !EXCLUDE_ALLEN,
  parts,
  concepts,
  chunks,
  triangles,
};
fs.writeFileSync(path.join(OUT, 'female.json'), JSON.stringify(manifest));

const csvq = (v) => (/[",\n]/.test(v) ? `"${String(v).replace(/"/g, '""')}"` : v);
fs.writeFileSync(ID_MAP, ['mesh_name,concept_id,concept_name,source,reviewed_by', ...rows.map((r) => r.map(csvq).join(','))].join('\n') + '\n');

const bySystem = {};
parts.forEach((p) => (bySystem[p.system] = (bySystem[p.system] ?? 0) + 1));
const report = {
  excludeAllen: EXCLUDE_ALLEN,
  glb: path.relative(HERE, GLB), meshNodes: meshNodes.length, nodes: N.length, bakedTransforms: transformed,
  boundsCheck: { skinExtent, wholeModelExtent: extent, candidates, chosen: { scale: chosen.scale, up: chosen.up } },
  placementShiftM: shift, sourceTriangles: triangles, srcChunks: chunks.length, srcBytes: chunks.reduce((n, c) => n + c.bytes, 0),
  parts: parts.length, concepts: concepts.length, groupConcepts, bySystem, mapping: stats,
  mappedToOntology: stats.FMA + stats.UBERON, typoFixes: [...typoFixes],
};
fs.writeFileSync(REPORT, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
