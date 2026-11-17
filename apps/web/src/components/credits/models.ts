// Single source for 3D model credits. Text mirrors deploy/atlas/ATTRIBUTION.md.
// Keep the two in step: if a licence, version or list of changes is edited there, edit it here.

export type ModelId = 'bodyparts3d' | 'female-study' | 'hra-vh-f';

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
  'female-study': {
    id: 'female-study',
    title: 'Female study model v3 (human-atlas-enhanced)',
    version: 'v3, upstream commit fb3ca0f (model files from 7 September 2026)',
    creators:
      'BodyParts3D © DBCLS and Human Reference Atlas VH_F v1.5 (Kristen Browne, Heidi Schlehlein, HuBMAP); reshaped and fitted by the human-atlas-enhanced project (wiiiimm and PrejudiceNeutrino, fork of ashemag/human-atlas, MIT, © 2026 ashemag)',
    short: '3D model: female study model, BodyParts3D © DBCLS reshaped by human-atlas-enhanced (MIT) + HRA VH_F v1.5, CC BY 4.0',
    licenseName: 'CC BY 4.0',
    licenseUrl: CC_BY_URL,
    sourceUrl: 'https://github.com/PrejudiceNeutrino/human-atlas-enhanced',
    sourceLabel: 'human-atlas-enhanced on GitHub',
    extra: { label: 'Source DOI of the HRA female data 10.48539/HBM352.BTSQ.586', url: 'https://doi.org/10.48539/HBM352.BTSQ.586' },
    changes:
      'Upstream changes (human-atlas-enhanced, code MIT): 2,181 BodyParts3D 4.0 male meshes (CC BY 4.0) reshaped by morph fields to estimated female proportions (stature, torso, thorax, head, waist, glutes; described upstream as artistic estimates); 64 HRA VH_F v1.5 female meshes (CC BY 4.0) fitted into that body (pelvis to the hip-bone envelope, reproductive tract by one affine fit, breast by a contour); 53 male or pelvic-floor parts removed. Our changes: each part marked as reshaped male geometry or female HRA data; FMA ids written without a colon and ids uppercased; reproductive and breast parts grouped as "Reproductive (female)". Geometry bytes are unchanged.',
    note: 'An experimental study model for orientation, not female anatomy data throughout: 97% of its meshes are male anatomy reshaped to a female form, and the upstream authors say its review is unresolved. Only the 64 HRA parts come from female data. There is no vulva, clitoris, labia, female urethra or female pelvic floor. It is not a clinical tool.',
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
      'In the Female view (the female study model), 64 of these meshes (uterus, uterine tubes, ovaries, vagina and their ligaments, the breasts, the pelvic bones and two knee ligaments) are fitted into the reshaped body by human-atlas-enhanced: affine fits for the pelvis and reproductive tract, a contour for the breast; their names and ontology ids are kept, FMA ids written without the colon. Our earlier organs-only build of this set, kept as a fallback and not shown by default since 17 November 2026: source geometry the HRA 3d-vh-f-united.glb (cdn.humanatlas.io, v1.5). Native metre, Y-up coordinates translated onto the stage; coincident vertices welded and source normals averaged; geometry simplified with a 0.2% per-structure relative error bound; normals quantised; mesh names cleaned for display (underscores removed, _L/_R written as Left/Right, a few source typos corrected); each mesh mapped by us to an FMA, UBERON or synthetic HRA concept id (from the ontology ids in the file where present); colours and display systems curated for this viewer. The 282 Allen Institute brain-region meshes are left out until their licence is confirmed, so 606 of the 888 source meshes are shown, with 832 selectable individual or compound concepts.',
    note: 'This is a reference assembly with whole-body surface and selected organs, including female reproductive anatomy. Skeleton and muscle coverage is partial and brain regions are not included. It is not a complete model of every structure and it is not a single-person scan. Eight placenta and umbilical structures sit under "Pregnancy reference" and are hidden by default. The HRA dataset credits the NLM Visible Human Project (U.S. National Library of Medicine), the source of the Visible Human Female body.',
  },
};

export const MODEL_ORDER: ModelId[] = ['bodyparts3d', 'female-study', 'hra-vh-f'];
