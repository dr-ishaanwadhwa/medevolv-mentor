// Extract the two optic-chiasm parts (FMA62045) from the local human-atlas build into a tiny file the landing loads
// instead of the 3.7 MB atlas.json + body chunk (PRD 4.L, L-6).
//
//   node scripts/extract_chiasm.mjs [path/to/human-atlas/public/models]
//
// Output: apps/web/public/landing/chiasm.bin (+ chiasm.json sidecar with the source atlas version and credit).
// chiasm.bin (little endian):
//   magic 'CHI1', u32 parts, u32 totalVertices, u32 totalIndices,
//   per part: u32 vertexCount, u32 indexCount,
//   float32 positions[3*V] (already centred, scaled so the longest side is 1.3, same as story/chiasm.ts),
//   int16 normals[3*V] (normalised, as in the atlas), padded to 4 bytes,
//   uint16 indices[I] (part-local), padded to 4 bytes.
// The mesh is BodyParts3D, (c) DBCLS, CC BY 4.0; the landing shows that credit next to it.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '..');
const models = process.argv[2] ?? path.join(root, '../third_party/human-atlas/public/models');
const outDir = path.join(root, 'apps/web/public/landing');

const atlas = JSON.parse(fs.readFileSync(path.join(models, 'atlas.json'), 'utf8'));
const parts = atlas.parts.filter((p) => String(p.conceptId).toUpperCase() === 'FMA62045');
if (!parts.length) throw new Error('FMA62045 not in atlas');

function chunkBuffer(ci) {
  const c = atlas.chunks[ci];
  const gz = path.join(models, path.basename(c.gzip ?? ''));
  const raw = path.join(models, path.basename(c.url));
  const buf = fs.existsSync(raw) ? fs.readFileSync(raw) : zlib.gunzipSync(fs.readFileSync(gz));
  if (buf.byteLength !== c.bytes) throw new Error(`chunk ${ci} size mismatch`);
  return buf;
}

const lo = [Infinity, Infinity, Infinity];
const hi = [-Infinity, -Infinity, -Infinity];
const got = parts.map((p) => {
  const b = chunkBuffer(p.chunk);
  const pos = new Float32Array(b.buffer.slice(b.byteOffset + p.positions, b.byteOffset + p.positions + p.vertexCount * 12));
  const nor = new Int16Array(b.buffer.slice(b.byteOffset + p.normals, b.byteOffset + p.normals + p.vertexCount * 6));
  const idx = new Uint32Array(b.buffer.slice(b.byteOffset + p.indices, b.byteOffset + p.indices + p.indexCount * 4));
  for (let i = 0; i < pos.length; i++) { const a = i % 3; lo[a] = Math.min(lo[a], pos[i]); hi[a] = Math.max(hi[a], pos[i]); }
  if (Math.max(...idx) > 65535) throw new Error('index does not fit uint16');
  return { pos, nor, idx, p };
});
const c = lo.map((v, i) => (v + hi[i]) / 2);
const k = 1.3 / Math.max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]);
const V = got.reduce((s, g) => s + g.p.vertexCount, 0);
const I = got.reduce((s, g) => s + g.p.indexCount, 0);
const pad4 = (n) => (n + 3) & ~3;
const head = 16 + 8 * got.length;
const posOff = head, norOff = posOff + V * 12, idxOff = norOff + pad4(V * 6);
const out = Buffer.alloc(idxOff + pad4(I * 2));
out.write('CHI1', 0, 'ascii');
out.writeUInt32LE(got.length, 4); out.writeUInt32LE(V, 8); out.writeUInt32LE(I, 12);
let pv = 0, pi = 0, ni = 0, ii = 0;
got.forEach((g, n) => {
  out.writeUInt32LE(g.p.vertexCount, 16 + n * 8); out.writeUInt32LE(g.p.indexCount, 20 + n * 8);
  for (let i = 0; i < g.pos.length; i++) out.writeFloatLE((g.pos[i] - c[i % 3]) * k, posOff + (pv + i) * 4);
  for (let i = 0; i < g.nor.length; i++) out.writeInt16LE(g.nor[i], norOff + (ni + i) * 2);
  for (let i = 0; i < g.idx.length; i++) out.writeUInt16LE(g.idx[i], idxOff + (ii + i) * 2);
  pv += g.pos.length; ni += g.nor.length; ii += g.idx.length; pi += g.p.indexCount;
});
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'chiasm.bin'), out);
fs.writeFileSync(path.join(outDir, 'chiasm.json'), JSON.stringify({
  concept: 'FMA62045', label: 'Optic chiasm', parts: got.map((g) => g.p.id), vertices: V, indices: I, bytes: out.length,
  source: { atlas_version: atlas.version, sex: atlas.sex, extracted: new Date().toISOString().slice(0, 10) },
  credit: 'BodyParts3D, (c) DBCLS, CC BY 4.0, https://creativecommons.org/licenses/by/4.0/',
}, null, 1) + '\n');
console.log(`chiasm.bin ${out.length} bytes, ${got.length} parts, ${V} vertices, ${I} indices`);
