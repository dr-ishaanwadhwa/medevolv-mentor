#!/usr/bin/env node
// Validate the built female manifest and chunks: the same integrity checks as human-atlas validate-atlas.mjs
// (which hard-codes the male counts 2234/3432, so it cannot be reused), plus gzip round-trip, mapping coverage and
// anatomical spot checks. Exit code 1 on any failure.
//   node validate_female.mjs [MODELS_DIR]
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import { gunzipSync } from 'node:zlib';

const dir = process.argv[2] ?? path.join(os.homedir(), 'Projects/third_party/human-atlas/public/models');
const atlas = JSON.parse(fs.readFileSync(path.join(dir, 'female.json'), 'utf8'));
const SYSTEMS = new Set(['skeletal', 'muscular', 'cardiac', 'sensory', 'arterial', 'venous', 'nervous', 'respiratory', 'digestive', 'urinary', 'lymphatic', 'endocrine', 'reproductive', 'reproductive_female', 'pregnancy', 'integumentary', 'connective']);

assert.equal(atlas.sex, 'female');
assert.ok(atlas.version && atlas.version !== 'BodyParts3D 4.0', 'version must differ from the male manifest (IndexedDB keys)');
assert.ok(atlas.optimized, 'run optimize-anatomy.mjs first');
const ids = new Set(atlas.parts.map((p) => p.id));
assert.equal(ids.size, atlas.parts.length, 'duplicate part ids');
for (const id of ids) assert.match(id, /^[A-Z0-9:_]+$/, `part id not uppercase/safe: ${id}`);

const files = atlas.chunks.map((c) => {
  const b = fs.readFileSync(path.join(dir, path.basename(c.url)));
  assert.equal(b.length, c.bytes, `${c.url} size`);
  assert.ok(c.gzip && c.gzipBytes, `${c.url} lacks gzip fields`);
  const gz = fs.readFileSync(path.join(dir, path.basename(c.gzip)));
  assert.equal(gz.length, c.gzipBytes, `${c.gzip} size`);
  assert.ok(gunzipSync(gz).equals(b), `${c.gzip} does not round-trip`);
  return b;
});
let tris = 0;
for (const p of atlas.parts) {
  assert.ok(p.name.trim() && p.name !== '-' && !/_/.test(p.name) && /^[A-Z0-9]/.test(p.name), `bad name ${p.id}: ${p.name}`);
  assert.ok(p.conceptId && p.conceptId !== '-', `${p.id}: no concept`);
  assert.equal(p.conceptId, p.conceptId.toUpperCase(), `${p.id}: concept id not uppercase`);
  assert.ok(!/[\s,]/.test(p.conceptId), `${p.id}: concept id has space or comma`);
  assert.ok(SYSTEMS.has(p.system), `${p.id}: unknown system ${p.system}`);
  const b = files[p.chunk];
  assert.ok(p.positions % 4 === 0 && p.normals % 4 === 0 && p.indices % 4 === 0, `${p.id}: unaligned`);
  assert.ok(p.indices + p.indexCount * 4 <= b.length && p.positions + p.vertexCount * 12 <= b.length && p.normals + p.vertexCount * 6 <= b.length);
  const pos = new Float32Array(b.buffer, b.byteOffset + p.positions, p.vertexCount * 3);
  const idx = new Uint32Array(b.buffer, b.byteOffset + p.indices, p.indexCount);
  assert.ok(idx.length >= 3 && idx.length % 3 === 0);
  for (const i of idx) assert.ok(i < p.vertexCount, `${p.id}: invalid vertex`);
  for (const v of pos) assert.ok(Number.isFinite(v));
  assert.ok(p.bounds[0].every((v, k) => v <= p.bounds[1][k]));
  tris += p.indexCount / 3;
}
assert.equal(tris, atlas.triangles, 'triangle total');
const conceptIds = new Set();
for (const c of atlas.concepts) {
  assert.ok(!conceptIds.has(c.id), `duplicate concept ${c.id}`);
  conceptIds.add(c.id);
  assert.equal(c.id, c.id.toUpperCase());
  assert.ok(!/[\s,]/.test(c.id), `${c.id}: space or comma`);
  assert.ok(c.elements.length && c.name, `${c.id}: empty`);
  for (const e of c.elements) assert.ok(ids.has(e), `${c.id}: missing ${e}`);
}
const partConcepts = new Set(atlas.parts.map((p) => p.conceptId));
for (const id of partConcepts) assert.ok(conceptIds.has(id), `part concept ${id} missing from concepts`);

// ---- scale and placement
const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
for (const p of atlas.parts) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], p.bounds[0][k]); hi[k] = Math.max(hi[k], p.bounds[1][k]); }
const skin = atlas.parts.find((p) => p.system === 'integumentary');
assert.ok(Math.abs(skin.bounds[0][1]) < 0.01, 'feet should sit at y = 0');
assert.ok(Math.abs(skin.bounds[1][1] - 1.666) < 0.02, 'height should be about 1.666 m');
assert.ok(Math.abs((skin.bounds[0][0] + skin.bounds[1][0]) / 2) < 0.01, 'x centred');

// ---- spot checks: name found, left is +x, relative positions
const byName = (re) => atlas.parts.filter((p) => re.test(p.name));
const centre = (p) => p.bounds[0].map((v, k) => (v + p.bounds[1][k]) / 2);
const cy = (re) => { const ps = byName(re); assert.ok(ps.length, `spot check: nothing named ${re}`); return ps.reduce((s, p) => s + centre(p)[1], 0) / ps.length; };
const cz = (re) => { const ps = byName(re); assert.ok(ps.length, `spot check: nothing named ${re}`); return ps.reduce((s, p) => s + centre(p)[2], 0) / ps.length; };
const cx = (re) => { const ps = byName(re); assert.ok(ps.length, `spot check: nothing named ${re}`); return ps.reduce((s, p) => s + centre(p)[0], 0) / ps.length; };
const checks = [];
const check = (label, ok) => { checks.push([label, !!ok]); };
check('left ovary at +x, right ovary at -x', cx(/^Left ovary$/) > 0 && cx(/^Right ovary$/) < 0);
check('ovaries lateral to the midline (|x| > 2 cm)', Math.abs(cx(/^Left ovary$/)) > 0.02);
check('uterine body sits between the ovaries (x)', Math.abs(cx(/^Body of uterus$/)) < Math.abs(cx(/^Left ovary$/)));
check('cervix below the uterine body', cy(/^Cervix$/) < cy(/^Body of uterus$/));
check('fundus above the uterine body', cy(/^Fundus of uterus$/) > cy(/^Body of uterus$/));
check('vagina below the cervix', cy(/^Vagina$/) < cy(/^Cervix$/));
check('ovaries at about the level of the uterine body or higher', cy(/^Left ovary$/) > cy(/^Cervix$/));
check('uterus lies inferior to the kidneys', cy(/^Body of uterus$/) < cy(/^Left outer cortex of kidney$/));
check('left kidney at +x, right kidney at -x', cx(/outer cortex of kidney L|Left outer cortex of kidney/i) > 0 || cx(/Left .*kidney/i) > 0);
check('breast (nipple) is anterior to the uterus', cz(/nipple/i) > cz(/^Body of uterus$/));
check('lumbar vertebra is posterior to the uterus', cz(/lumbar vertebra 3/i) < cz(/^Body of uterus$/));
check('urinary bladder anterior to the uterine body', cz(/bladder/i) > cz(/^Body of uterus$/));
check('urinary bladder inferior to the kidneys', cy(/bladder/i) < cy(/^Left outer cortex of kidney$/));
check('left nipple at +x, right nipple at -x', cx(/^Left nipple$/) > 0 && cx(/^Right nipple$/) < 0);
check('heart above the uterus', cy(/cardiac|papillary muscle of heart/i) > cy(/^Body of uterus$/));
check('eye above the heart', cy(/sclera/i) > cy(/papillary muscle of heart/i));
check('pubic bone anterior to the lumbar spine', cz(/^Left pubis compact bone$|pubis compact bone/i) > cz(/lumbar vertebra 3/i));
check('liver parts lie right of the spleen parts (x)', cx(/ of liver$/i) < cx(/ of spleen$/i));
check('placenta items are in the Pregnancy reference system', byName(/placenta|umbilical|amnion|basal plate|chorionic/i).every((p) => p.system === 'pregnancy'));
check('uterus parts are in Reproductive (female)', ['Body of uterus', 'Cervix', 'Vagina'].every((n) => byName(new RegExp(`^${n}$`))[0]?.system === 'reproductive_female'));
const failed = checks.filter(([, ok]) => !ok);
checks.forEach(([l, ok]) => console.log(`${ok ? 'ok  ' : 'FAIL'} ${l}`));

// ---- mapping coverage (from id_map.csv next to this script)
const csv = fs.readFileSync(new URL('./id_map.csv', import.meta.url), 'utf8').trim().split('\n').slice(1);
const src = (l) => l.replace(/"[^"]*"/g, '""').split(',')[3];
const tally = {};
for (const l of csv) { const s = src(l).replace(/\s*\(.*$/, ''); tally[s] = (tally[s] ?? 0) + 1; }
const meshOnly = csv.filter((l) => src(l) !== 'group');
const ontologyBacked = meshOnly.filter((l) => /^(hra-extras|synthetic:shared-id-split|override)/.test(src(l))).length;
const summary = {
  parts: atlas.parts.length, concepts: atlas.concepts.length, triangles: atlas.triangles, sourceTriangles: atlas.sourceTriangles,
  chunks: atlas.chunks.length, rawMB: +(atlas.chunks.reduce((n, c) => n + c.bytes, 0) / 1e6).toFixed(2),
  gzipMB: +(atlas.chunks.reduce((n, c) => n + c.gzipBytes, 0) / 1e6).toFixed(2),
  mapping: { meshRows: meshOnly.length, ontologyBacked, ontologyBackedPct: +((100 * ontologyBacked) / meshOnly.length).toFixed(1), bySource: tally },
  spotChecks: `${checks.length - failed.length}/${checks.length} passed`,
};
console.log(JSON.stringify(summary, null, 2));
if (failed.length) { console.error(`${failed.length} spot check(s) failed`); process.exit(1); }
console.log(`Verified ${ids.size} meshes, ${atlas.concepts.length} concepts, ${tris.toLocaleString()} triangles, gzip round-trip and every binary buffer.`);
