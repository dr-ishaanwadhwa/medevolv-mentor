/** Parser for public/landing/chiasm.bin (format written by scripts/extract_chiasm.mjs). Pure, so the unit test can read
 * the real file. The landing loads this instead of the atlas manifest and chunk (L-6). */

export interface ChiasmPart {
  positions: Float32Array;
  /** normalised int16 normals, 3 per vertex */
  normals: Int16Array;
  indices: Uint16Array;
}

const pad4 = (n: number) => (n + 3) & ~3;

export function parseChiasm(buf: ArrayBuffer): ChiasmPart[] {
  if (buf.byteLength < 16) throw new Error('chiasm.bin too short');
  const magic = String.fromCharCode(...new Uint8Array(buf, 0, 4));
  if (magic !== 'CHI1') throw new Error('chiasm.bin bad magic');
  const dv = new DataView(buf);
  const n = dv.getUint32(4, true);
  const V = dv.getUint32(8, true);
  const I = dv.getUint32(12, true);
  const head = 16 + 8 * n;
  const posOff = head;
  const norOff = posOff + V * 12;
  const idxOff = norOff + pad4(V * 6);
  if (buf.byteLength < idxOff + I * 2) throw new Error('chiasm.bin incomplete');
  const parts: ChiasmPart[] = [];
  let v = 0;
  let i = 0;
  for (let k = 0; k < n; k++) {
    const vc = dv.getUint32(16 + k * 8, true);
    const ic = dv.getUint32(20 + k * 8, true);
    parts.push({
      positions: new Float32Array(buf.slice(posOff + v * 12, posOff + (v + vc) * 12)),
      normals: new Int16Array(buf.slice(norOff + v * 6, norOff + (v + vc) * 6)),
      indices: new Uint16Array(buf.slice(idxOff + i * 2, idxOff + (i + ic) * 2)),
    });
    v += vc;
    i += ic;
  }
  if (v !== V || i !== I) throw new Error('chiasm.bin counts do not add up');
  return parts;
}
