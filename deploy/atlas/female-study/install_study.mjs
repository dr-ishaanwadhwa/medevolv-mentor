#!/usr/bin/env node
// Install the human-atlas-enhanced "female study model v3" as our female atlas set. No network, no dependencies.
//   node deploy/atlas/female-study/install_study.mjs <models-out-dir> [--sidecar rag/female_study_origin.json]
//
// Reads the downloaded upstream files in ./source (checked against ./SHA256SUMS.txt), then writes into <models-out-dir>:
//   female.json (+ .gz)                 the manifest our loader reads (apps/web/src/lib/atlas-sex.ts manifestFile)
//   female-base-N.bin(.gz), female-joint-additions-*.bin(.gz)   chunks, names unchanged; raw .bin is gunzipped here
// and the API sidecar (default rag/female_study_origin.json): which concept ids the female model draws with native
// HRA female meshes, with reshaped BodyParts3D (male) meshes, or with both.
//
// Changes to the upstream manifest (all additive or id-normalising; geometry bytes are untouched):
//   - part.origin: "hra-female" (provenance.source HRA) or "bp3d-reshaped" (provenance.source BodyParts3D)
//   - ids: "FMA:123" -> "FMA123" (our FMA form), every concept id and part conceptId uppercased (lookups are
//     case-insensitive; the crosswalk and ?select= expect uppercase, no spaces or commas)
//   - systems: upstream "reproductive" (HRA female tract) and "mammary" -> our "reproductive_female"
//   (upstream already has HRA:VH_F_UTERUS with the same 10 parts as our earlier HRA build, so old links keep working;
//   checked below)
//   - version, scope and source rewritten so caches never mix it with the earlier HRA organs-only set
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '../../..');
const SRC = path.join(HERE, 'source');
const UPSTREAM_COMMIT = 'fb3ca0f3950dafce4d262c3a0404959753796791';

const args = process.argv.slice(2);
const out = args[0];
if (!out) {
  console.error('usage: install_study.mjs <models-out-dir> [--sidecar path]');
  process.exit(2);
}
const si = args.indexOf('--sidecar');
const sidecar = si >= 0 ? path.resolve(args[si + 1]) : path.join(REPO, 'rag/female_study_origin.json');

const fail = (msg) => {
  console.error('install_study: ' + msg);
  process.exit(1);
};

// 1. checksums (the upstream repo publishes none; ours were recorded at download, see README.md)
const sums = fs.readFileSync(path.join(HERE, 'SHA256SUMS.txt'), 'utf8').trim().split('\n').map((l) => l.split(/\s+/));
for (const [want, name] of sums) {
  const f = path.join(SRC, name);
  if (!fs.existsSync(f)) fail(`missing ${f}; see deploy/atlas/female-study/README.md`);
  const got = crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
  if (got !== want) fail(`${name} sha256 ${got} does not match ${want}`);
}

// 2. manifest
const m = JSON.parse(fs.readFileSync(path.join(SRC, 'atlas-female-reconstructed.json'), 'utf8'));
const normId = (id) => String(id).trim().replace(/^FMA:(\d+)$/i, 'FMA$1').toUpperCase();
const SYSTEM = { reproductive: 'reproductive_female', mammary: 'reproductive_female' };
const origins = { 'hra-female': 0, 'bp3d-reshaped': 0 };
for (const p of m.parts) {
  const src = p.provenance?.source ?? '';
  if (/^HRA\b/.test(src)) p.origin = 'hra-female';
  else if (/^BodyParts3D\b/.test(src)) p.origin = 'bp3d-reshaped';
  else fail(`part ${p.id} has unknown provenance source ${JSON.stringify(src)}`);
  origins[p.origin]++;
  p.conceptId = normId(p.conceptId);
  p.system = SYSTEM[p.system] ?? p.system;
  if (/[\s,]/.test(p.conceptId)) fail(`part ${p.id} conceptId ${p.conceptId} has a space or comma`);
}
for (const c of m.concepts) c.id = normId(c.id);
const partIds = new Set(m.parts.map((p) => p.id));
const UTERUS = ['abdominal_ostium_of_uterine_tube', 'body_of_uterus', 'fundus_of_uterus', 'cornua', 'lower_uterine_segment',
  'posterior_wall_of_uterus', 'anterior_wall_of_uterus', 'cervix', 'internal_cervical_os', 'external_cervical_os'].map((n) => 'VH_F_' + n);
for (const e of UTERUS) if (!partIds.has(e)) fail(`uterus part ${e} missing`);
const uterus = m.concepts.find((c) => c.id === 'HRA:VH_F_UTERUS');
if (!uterus || [...UTERUS].sort().join() !== [...uterus.elements].sort().join()) fail('HRA:VH_F_UTERUS differs from our earlier HRA build');

// integrity: unique ids, every concept draws something, offsets inside their chunk
const seen = new Set();
for (const c of m.concepts) {
  if (seen.has(c.id)) fail(`duplicate concept id ${c.id}`);
  seen.add(c.id);
  if (!c.elements.some((e) => partIds.has(e))) fail(`concept ${c.id} draws no part`);
}
if (partIds.size !== m.parts.length) fail('duplicate part ids');
const byOrigin = (o) => m.parts.filter((p) => p.origin === o).length;
if (byOrigin('hra-female') !== 64 || byOrigin('bp3d-reshaped') !== 2181) fail(`origin counts changed: ${JSON.stringify(origins)}`);

// 3. chunks: copy .gz, gunzip to .bin, check both sizes and every part's byte ranges
fs.mkdirSync(out, { recursive: true });
for (const f of fs.readdirSync(out)) if (/^female(-\d+|-base-\d+|-joint-additions-[0-9a-f]+|-src-\d+)?\.(bin|bin\.gz|json|json\.gz)$/.test(f)) fs.rmSync(path.join(out, f));
const base = (u) => u.replace(/^\/?models\//, '');
m.chunks.forEach((ch, i) => {
  const gz = fs.readFileSync(path.join(SRC, base(ch.gzip)));
  if (gz.length !== ch.gzipBytes) fail(`${ch.gzip}: ${gz.length} bytes, manifest says ${ch.gzipBytes}`);
  const raw = zlib.gunzipSync(gz);
  if (raw.length !== ch.bytes) fail(`${ch.url}: ${raw.length} bytes after gunzip, manifest says ${ch.bytes}`);
  for (const p of m.parts.filter((x) => x.chunk === i)) {
    const ends = [p.positions + p.vertexCount * 12, p.indices + p.indexCount * 4];
    if (Math.max(...ends) > raw.length || p.normals >= raw.length) fail(`part ${p.id} reaches past ${ch.url}`);
    // the viewer builds Float32/Int16/Uint32 views straight on the chunk buffer, which need aligned offsets
    if (p.positions % 4 || p.normals % 2 || p.indices % 4) fail(`part ${p.id} has a misaligned offset`);
    for (let k = 0; k < p.indexCount; k++) {
      const v = raw.readUInt32LE(p.indices + k * 4);
      if (v >= p.vertexCount) fail(`part ${p.id} index ${v} >= vertexCount ${p.vertexCount}`);
    }
  }
  fs.writeFileSync(path.join(out, base(ch.gzip)), gz);
  fs.writeFileSync(path.join(out, base(ch.url)), raw);
});

// anatomical spot check: left is +x in this frame (same as the male model)
const cx = (id) => {
  const p = m.parts.find((x) => x.id === id);
  return (p.bounds[0][0] + p.bounds[1][0]) / 2;
};
if (!(cx('VH_F_left_ovary') > 0 && cx('VH_F_right_ovary') < 0)) fail('left ovary is not on +x');

// 4. manifest metadata
m.version = `female-study-v3@${UPSTREAM_COMMIT.slice(0, 7)}`;
m.sex = 'female';
m.source = 'human-atlas-enhanced female study model v3: BodyParts3D 4.0 (male) reshaped by morph fields + HRA VH_F v1.5 female parts';
m.scope = `Study model for orientation: ${origins['bp3d-reshaped']} male BodyParts3D meshes reshaped to a female form, ${origins['hra-female']} female meshes from the Human Reference Atlas. Experimental, not female anatomy data throughout.`;
m.origins = origins;
m.upstream = { repo: 'https://github.com/PrejudiceNeutrino/human-atlas-enhanced', commit: UPSTREAM_COMMIT, manifest: 'public/models/atlas-female-reconstructed.json' };
delete m.reconstructionReport; // the fit report is kept in source/ for provenance, not shipped
if (m.jointAdditions) delete m.jointAdditions.report;
const json = JSON.stringify(m);
fs.writeFileSync(path.join(out, 'female.json'), json);
fs.writeFileSync(path.join(out, 'female.json.gz'), zlib.gzipSync(json, { level: 9 }));

// 5. API sidecar: concept id -> origin of the parts the female model draws for it
const partOrigin = new Map(m.parts.map((p) => [p.id, p.origin]));
const drawn = new Map(); // id -> Set(origin)
const names = new Map();
const add = (id, name, origin) => {
  if (!drawn.has(id)) drawn.set(id, new Set());
  drawn.get(id).add(origin);
  if (name && !names.has(id)) names.set(id, name);
};
for (const c of m.concepts) for (const e of c.elements) if (partOrigin.has(e)) add(c.id, c.name, partOrigin.get(e));
for (const p of m.parts) add(p.conceptId, p.name, p.origin);
const car = { 'hra-female': {}, mixed: {}, 'bp3d-reshaped': [] };
for (const id of [...drawn.keys()].sort()) {
  const s = drawn.get(id);
  if (s.size > 1) car.mixed[id] = names.get(id);
  else if (s.has('hra-female')) car['hra-female'][id] = names.get(id);
  else car['bp3d-reshaped'].push(id);
}
const sidecarDoc = {
  about: 'Female study model (human-atlas-enhanced v3): which concept ids it draws with native HRA female meshes, with BodyParts3D male meshes reshaped to a female form, or both. Generated by deploy/atlas/female-study/install_study.mjs; do not edit.',
  model: m.version,
  ...car,
};
fs.writeFileSync(sidecar, JSON.stringify(sidecarDoc, null, 0) + '\n');

const gzTotal = m.chunks.reduce((n, c) => n + c.gzipBytes, 0);
console.log(
  `female study model installed in ${out}: ${m.parts.length} parts (${origins['hra-female']} hra-female, ${origins['bp3d-reshaped']} bp3d-reshaped), ` +
    `${m.concepts.length} concepts, ${m.chunks.length} chunks, ${gzTotal} gzip bytes, female.json ${json.length} bytes; sidecar ${path.relative(REPO, sidecar)}`,
);
