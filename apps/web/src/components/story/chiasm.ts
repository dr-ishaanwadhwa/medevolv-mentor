import * as THREE from 'three';
import { loadChunk } from '@/components/canvas/model-download';
import { modelUrl, type Atlas } from '@/lib/anatomy';

/** Loads only the optic-chiasm parts (concept FMA62045) from the atlas; resolves to a centred, unit-ish mesh group. */
export async function loadChiasm(): Promise<THREE.Group> {
  const res = await fetch(modelUrl('/models/atlas.json'));
  if (!res.ok) throw new Error('atlas.json');
  const atlas = (await res.json()) as Atlas;
  const parts = atlas.parts.filter((p) => p.conceptId.toUpperCase() === 'FMA62045');
  if (!parts.length) throw new Error('optic chiasm not in atlas');
  const group = new THREE.Group();
  const chunkIds = [...new Set(parts.map((p) => p.chunk))];
  const geoms: THREE.BufferGeometry[] = [];
  for (const ci of chunkIds) {
    const buffer = await loadChunk(atlas, atlas.chunks[ci]);
    for (const p of parts.filter((x) => x.chunk === ci)) {
      const g = new THREE.BufferGeometry();
      // copy out of the shared chunk so the big buffer can be released
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(buffer.slice(p.positions, p.positions + p.vertexCount * 12)), 3));
      g.setAttribute('normal', new THREE.BufferAttribute(new Int16Array(buffer.slice(p.normals, p.normals + p.vertexCount * 6)), 3, true));
      g.setIndex(new THREE.BufferAttribute(new Uint32Array(buffer.slice(p.indices, p.indices + p.indexCount * 4)), 1));
      geoms.push(g);
    }
  }
  const box = new THREE.Box3();
  geoms.forEach((g) => { g.computeBoundingBox(); box.union(g.boundingBox!); });
  const c = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const k = 1.05 / Math.max(size.x, size.y, size.z);
  const mat = new THREE.MeshStandardMaterial({ color: '#d8b565', roughness: 0.45, metalness: 0.05, transparent: true, opacity: 0, emissive: '#6b4a10', emissiveIntensity: 0.25 });
  geoms.forEach((g) => {
    g.translate(-c.x, -c.y, -c.z);
    g.scale(k, k, k);
    group.add(new THREE.Mesh(g, mat));
  });
  group.userData.material = mat;
  return group;
}
