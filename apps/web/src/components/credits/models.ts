// Single source for 3D model credits. Text mirrors deploy/atlas/ATTRIBUTION.md.
// Keep the two in step: if a licence, version or list of changes is edited there, edit it here.

export type ModelId = 'bodyparts3d' | 'hra-vh-f';

export interface ModelCreditInfo {
  id: ModelId;
  /** Full title of the work. */
  title: string;
  version: string;
  creators: string;
  /** Short line for under a 3D view. */
  short: string;
  licenseName: string;
  licenseUrl: string;
  sourceUrl: string;
  sourceLabel: string;
  /** Extra link, for example the publication or DOI. */
  extra?: { label: string; url: string };
  changes: string;
  note: string;
}

export const CC_BY_URL = 'https://creativecommons.org/licenses/by/4.0/';

export const MODELS: Record<ModelId, ModelCreditInfo> = {
  bodyparts3d: {
    id: 'bodyparts3d',
    title: 'BodyParts3D',
    version: '4.0 (isa_BP3D_4.0_obj_99)',
    creators: 'The Database Center for Life Science (DBCLS)',
    short: '3D model: BodyParts3D, © DBCLS, CC BY 4.0',
    licenseName: 'CC BY 4.0',
    licenseUrl: CC_BY_URL,
    sourceUrl: 'https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html',
    sourceLabel: 'BodyParts3D download page',
    extra: {
      label: 'Mitsuhashi et al. (2009), Nucleic Acids Research',
      url: 'https://doi.org/10.1093/nar/gkn613',
    },
    changes:
      'Axes and units converted from millimetres, Z-up to metres, Y-up; translated to rest on the stage; geometry simplified with meshoptimizer (0.2% relative error limit per structure); normals quantised to signed 16-bit; packed into binary chunks; display system groupings and colours curated for this viewer. All 2,234 source meshes remain represented; the combined hierarchy has 3,432 named FMA concepts. English names and relationships come from the IS-A and PART-OF tables in the same archive.',
    note: 'BodyParts3D is an adult male reference anatomy. It is not a complete model of every structure or variation, and it is not a clinical tool. The database licence page (updated 2025-02-27) permits redistribution and adaptation under CC BY 4.0; it supersedes the older CC BY-SA 2.1 Japan wording in some source file comments.',
  },
  'hra-vh-f': {
    id: 'hra-vh-f',
    title: '3D Reference Organ Set for Female (VH_F United)',
    version: 'v1.5 (2023)',
    creators: 'Kristen Browne and Heidi Schlehlein, Human Reference Atlas / HuBMAP',
    short: '3D model: Human Reference Atlas VH_F v1.5, CC BY 4.0',
    licenseName: 'CC BY 4.0',
    licenseUrl: CC_BY_URL,
    sourceUrl: 'https://lod.humanatlas.io/ref-organ/united-female/v1.5',
    sourceLabel: 'Human Reference Atlas dataset page',
    extra: { label: 'Source DOI 10.48539/HBM352.BTSQ.586', url: 'https://doi.org/10.48539/HBM352.BTSQ.586' },
    changes:
      'Source geometry: the HRA 3d-vh-f-united.glb (cdn.humanatlas.io, v1.5). Native metre, Y-up coordinates translated onto the stage; coincident vertices welded and source normals averaged; geometry simplified with a 0.2% per-structure relative error bound; normals quantised; mesh names cleaned for display (underscores removed, _L/_R written as Left/Right, a few source typos corrected); each mesh mapped by us to an FMA, UBERON or synthetic HRA concept id (from the ontology ids in the file where present); colours and display systems curated for this viewer. The 282 Allen Institute brain-region meshes are left out until their licence is confirmed, so 606 of the 888 source meshes are shown, with 832 selectable individual or compound concepts.',
    note: 'This is a reference assembly with whole-body surface and selected organs, including female reproductive anatomy. Skeleton and muscle coverage is partial and brain regions are not included. It is not a complete model of every structure and it is not a single-person scan. Eight placenta and umbilical structures sit under "Pregnancy reference" and are hidden by default. The HRA dataset credits the NLM Visible Human Project (U.S. National Library of Medicine), the source of the Visible Human Female body.',
  },
};

export const MODEL_ORDER: ModelId[] = ['bodyparts3d', 'hra-vh-f'];
