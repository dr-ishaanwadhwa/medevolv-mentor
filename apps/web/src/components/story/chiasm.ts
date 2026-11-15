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
  const k = 1.3 / Math.max(size.x, size.y, size.z);
  const mat = new THREE.MeshPhysicalMaterial({ color: '#2a7f88', roughness: 0.34, metalness: 0.05, clearcoat: 0.9, clearcoatRoughness: 0.2, sheen: 0.6, sheenColor: new THREE.Color('#9fe3ec'), transparent: true, opacity: 0 });
  const rim = { value: new THREE.Color('#8fe3ee') };
  // fresnel rim glow: edges catch the accent colour, so it reads as a lit specimen
  mat.onBeforeCompile = (sh) => {
    sh.uniforms.uRim = rim;
    sh.fragmentShader = 'uniform vec3 uRim;\n' + sh.fragmentShader.replace(
      '#include <opaque_fragment>',
      'float fr = pow(1.0 - clamp(dot(normalize(vViewPosition), normal), 0.0, 1.0), 2.6);\noutgoingLight += uRim * fr * 0.9;\n#include <opaque_fragment>',
    );
  };
  const wireMat = new THREE.MeshBasicMaterial({ color: '#4fb3bd', wireframe: true, transparent: true, opacity: 0, depthWrite: false });
  geoms.forEach((g) => {
    g.translate(-c.x, -c.y, -c.z);
    g.scale(k, k, k);
    group.add(new THREE.Mesh(g, mat));
    const w = new THREE.Mesh(g, wireMat);
    w.scale.setScalar(1.015);
    group.add(w);
  });
  group.userData = { material: mat, wireMat, rim };
  return group;
}
