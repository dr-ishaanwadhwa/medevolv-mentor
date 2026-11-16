import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parseChiasm } from './chiasm-bin';

const file = (n: string) => fileURLToPath(new URL(`../../../public/landing/${n}`, import.meta.url));

describe('chiasm.bin (L-6)', () => {
  it('parses the shipped file: two parts, counts match the sidecar, indices in range', () => {
    const b = readFileSync(file('chiasm.bin'));
    const meta = JSON.parse(readFileSync(file('chiasm.json'), 'utf8'));
    const parts = parseChiasm(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));
    expect(parts).toHaveLength(meta.parts.length);
    expect(parts.reduce((n, p) => n + p.positions.length / 3, 0)).toBe(meta.vertices);
    expect(parts.reduce((n, p) => n + p.indices.length, 0)).toBe(meta.indices);
    for (const p of parts) {
      const v = p.positions.length / 3;
      expect(Math.max(...p.indices)).toBeLessThan(v);
      expect(p.normals.length).toBe(p.positions.length);
    }
    expect(b.byteLength).toBeLessThan(100_000); // tens of KB, never the 3.7 MB atlas path
  });
  it('rejects a wrong file', () => {
    expect(() => parseChiasm(new ArrayBuffer(32))).toThrow();
  });
});
