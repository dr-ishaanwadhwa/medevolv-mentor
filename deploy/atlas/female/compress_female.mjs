#!/usr/bin/env node
// gzip the female chunks and record `gzip` / `gzipBytes` in female.json (same fields the male set has), then write
// `.json.gz` siblings for the manifests (atlas.json.gz, female.json.gz) so Caddy's `precompressed gzip` serves them
// compressed. The human-atlas compress-models.mjs only handles atlas.json, so this is the female equivalent.
//   node compress_female.mjs [MODELS_DIR]
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { gzipSync } from 'node:zlib';

const dir = process.argv[2] ?? path.join(os.homedir(), 'Projects/third_party/human-atlas/public/models');
const file = path.join(dir, 'female.json');
const atlas = JSON.parse(fs.readFileSync(file, 'utf8'));
let total = 0;
for (const c of atlas.chunks) {
  const gz = gzipSync(fs.readFileSync(path.join(dir, path.basename(c.url))), { level: 9 });
  c.gzip = `${c.url}.gz`;
  c.gzipBytes = gz.length;
  fs.writeFileSync(path.join(dir, path.basename(c.gzip)), gz);
  total += gz.length;
}
fs.writeFileSync(file, JSON.stringify(atlas));
const sizes = {};
for (const name of ['female.json', 'atlas.json']) {
  const p = path.join(dir, name);
  if (!fs.existsSync(p)) continue;
  const gz = gzipSync(fs.readFileSync(p), { level: 9 });
  fs.writeFileSync(`${p}.gz`, gz);
  sizes[name] = { bytes: fs.statSync(p).size, gzipBytes: gz.length };
}
console.log(JSON.stringify({ chunks: atlas.chunks.length, chunkGzipBytes: total, chunkGzipMB: +(total / 1e6).toFixed(2), manifests: sizes }));
