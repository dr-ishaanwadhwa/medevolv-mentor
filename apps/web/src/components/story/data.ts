export interface Neighbour { i: number; sim: number; book?: string }
export interface StoryBook { id: string; title: string; count: number; centroid: number[]; galaxy_centroid: number[] }
export interface Evidence { n: number; i: number; book: string; sim: number; where: string; cited: boolean }
export interface StoryJson {
  n: number;
  books: StoryBook[];
  min_similarity: number;
  journey: {
    question: string;
    sub_questions: string[];
    near: { query: string; neighbours: Neighbour[] }[];
    evidence: Evidence[];
  };
  answer: string;
  refusal?: { question: string; text?: string };
  declined?: { question: string; best: number; neighbours: Neighbour[] };
}

export interface StoryData {
  story: StoryJson;
  /** rendered point count (after optional subsampling) */
  count: number;
  galaxy: Float32Array;
  cluster: Float32Array;
  book: Float32Array;
  seed: Float32Array;
  mask: Float32Array; // vec4 per point
  /** original index -> rendered index (-1 if dropped) */
  remap: Int32Array | null;
  /** full-resolution layouts, for looking up specials */
  galaxyAll: Float32Array;
  clusterAll: Float32Array;
  subs: string[];
}

export async function loadStory(mobile: boolean, signal?: AbortSignal): Promise<StoryData> {
  const [sj, buf] = await Promise.all([
    fetch('/story/story.json', { signal }).then((r) => {
      if (!r.ok) throw new Error('story.json');
      return r.json() as Promise<StoryJson>;
    }),
    fetch('/story/library.bin', { signal }).then((r) => {
      if (!r.ok) throw new Error('library.bin');
      return r.arrayBuffer();
    }),
  ]);
  const N = sj.n;
  let galaxyAll: Float32Array;
  let clusterAll: Float32Array;
  let bookAll: Uint8Array;
  const magic = new Uint8Array(buf, 0, Math.min(4, buf.byteLength));
  if (magic.length === 4 && String.fromCharCode(...magic) === 'LIB2') {
    // LIB2: 16-byte header (magic, uint32 N, float32 scale), Int16 galaxy, Int16 cluster, Uint8 book
    if (buf.byteLength < 16 + N * 25) throw new Error('library.bin is incomplete');
    const dv = new DataView(buf);
    const scale = dv.getFloat32(8, true);
    const k = scale / 32767;
    const gq = new Int16Array(buf, 16, N * 3);
    const cq = new Int16Array(buf, 16 + N * 6, N * 3);
    galaxyAll = new Float32Array(N * 3);
    clusterAll = new Float32Array(N * 3);
    for (let j = 0; j < N * 3; j++) {
      galaxyAll[j] = gq[j] * k;
      clusterAll[j] = cq[j] * k;
    }
    bookAll = new Uint8Array(buf, 16 + N * 12, N);
  } else {
    // legacy: Float32 galaxy, Float32 cluster, Uint8 book
    if (buf.byteLength < N * 25) throw new Error('library.bin is incomplete');
    galaxyAll = new Float32Array(buf, 0, N * 3);
    clusterAll = new Float32Array(buf, N * 12, N * 3);
    bookAll = new Uint8Array(buf, N * 24, N);
  }

  const near = sj.journey?.near ?? [];
  const evidence = sj.journey?.evidence ?? [];
  const decl = sj.declined?.neighbours ?? [];
  const searchSet = new Set<number>();
  near.forEach((q) => q.neighbours.forEach((x) => searchSet.add(x.i)));
  const evSet = new Set(evidence.map((e) => e.i));
  const citedSet = new Set(evidence.filter((e) => e.cited).map((e) => e.i));
  const declSet = new Set(decl.map((x) => x.i));

  const keep: number[] = [];
  for (let i = 0; i < N; i++) {
    if (!mobile || i % 3 === 0 || searchSet.has(i) || evSet.has(i) || declSet.has(i)) keep.push(i);
  }
  const count = keep.length;
  const galaxy = new Float32Array(count * 3);
  const cluster = new Float32Array(count * 3);
  const book = new Float32Array(count);
  const seed = new Float32Array(count);
  const mask = new Float32Array(count * 4);
  const remap = mobile ? new Int32Array(N).fill(-1) : null;
  for (let k = 0; k < count; k++) {
    const i = keep[k];
    if (remap) remap[i] = k;
    galaxy.set(galaxyAll.subarray(i * 3, i * 3 + 3), k * 3);
    cluster.set(clusterAll.subarray(i * 3, i * 3 + 3), k * 3);
    book[k] = bookAll[i];
    // cheap deterministic hash in [0,1)
    seed[k] = ((Math.imul(i + 1, 2654435761) >>> 8) & 0xffff) / 65536;
    mask[k * 4] = searchSet.has(i) ? 1 : 0;
    mask[k * 4 + 1] = evSet.has(i) ? 1 : 0;
    mask[k * 4 + 2] = declSet.has(i) ? 1 : 0;
    mask[k * 4 + 3] = citedSet.has(i) ? 1 : 0;
  }
  const q = sj.journey?.question ?? '';
  let subs = (sj.journey?.sub_questions ?? []).filter((s) => s.trim() && s.trim() !== q.trim());
  if (!subs.length && q) subs = [q];
  return { story: sj, count, galaxy, cluster, book, seed, mask, remap, galaxyAll, clusterAll, subs };
}

/** Pretty short book name: "Essentials of Medical Pharmacology (7th ed.)" -> "Essentials of Medical Pharmacology" */
export const shortTitle = (t: string) => t.replace(/\s*\(.*?\)\s*$/, '');
export const bookNick: Record<string, string> = {
  grays: "Gray's Anatomy", guyton: 'Guyton & Hall', tripathi: 'Tripathi', robbins: 'Robbins',
  micro: 'Microbiology', davidson: "Davidson's", harrison: "Harrison's",
};
