# Anatomy data attribution

BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International.

- License: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html (updated 2025-02-27)
- Dataset: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html
- License terms: https://creativecommons.org/licenses/by/4.0/
- Source geometry: `isa_BP3D_4.0_obj_99.zip`, BodyParts3D 4.0.
- English names and relationships: IS-A and PART-OF concept, element, and inclusion tables from the same archive.
- Publication: Mitsuhashi et al. (2009), BodyParts3D: 3D structure database for anatomical concepts. https://doi.org/10.1093/nar/gkn613

Adaptations: axes and units converted from millimeters/Z-up to meters/Y-up; translated to rest at the stage; geometry simplified using meshoptimizer with 0.2% relative error limit per structure; normals quantized to signed 16-bit; packed into binary chunks; curated display system groupings and colors. The source contains 2,234 individual OBJ meshes; all remain represented. The combined hierarchy contains 3,432 named FMA concepts, which may reference multiple meshes. Original source identity is preserved in the manifest.

Source OBJ comments mention an older CC BY-SA 2.1 Japan license. The official current database license linked above supersedes that legacy text and explicitly permits redistribution and adaptation under CC BY 4.0.

BodyParts3D represents an adult male reference anatomy based on TARO MRI and anatomical illustration refinements. It is not a complete model of every possible human anatomical structure or variation. This interface is educational and is not a clinical tool.

## Female reference model (current release, behind the `female_atlas` flag)

Kristen Browne and Heidi Schlehlein, Human Reference Atlas / HuBMAP, *3D Reference Organ Set for United, Female*, v1.5 (created 2023-12-15). CC BY 4.0.

- Source DOI: https://doi.org/10.48539/HBM352.BTSQ.586 (resolves to https://purl.humanatlas.io/ref-organ/united-female/v1.5; creators, licence and the placement metadata below were read there on 2026-11-15)
- Dataset page: https://lod.humanatlas.io/ref-organ/united-female/v1.5
- Source geometry: https://cdn.humanatlas.io/digital-objects/ref-organ/united-female/v1.5/assets/3d-vh-f-united.glb
- License: https://creativecommons.org/licenses/by/4.0/ (no share-alike)
- Downloaded 2026-11-15 (the file's last-modified header is 2026-06-10): 211,624,968 bytes, SHA-256 `472567a56896b9b7890508da6501fbf858e56aaa30745365f7a71ade782b529c` (also in `deploy/atlas/female/source/3d-vh-f-united.glb.sha256`; the GLB itself is not in git).
- The HRA metadata also credits the NLM Visible Human Project (source of the Visible Human Female body) and the Allen Institute for Brain Science (the 282 `Allen_*` brain-region meshes).

Adaptations (CC BY 4.0 requires changes to be indicated): the GLB is metres, Y-up, left = +x, anterior = +z (the same frame as our male model), so no unit or axis conversion was needed (checked: skin extent 967.4 x 1666.3 x 329.3 mm matches the HRA metadata box within 0.1%; the -90 degree X rotation and millimetre translation in the HRA placement metadata map the file into the HRA global frame and are not applied); translated so the skin rests at y = 0 and is centred on x and z; coincident vertices welded and source normals averaged; geometry simplified with meshoptimizer at a 0.2% per-structure relative error bound; normals quantised to signed 16-bit; packed into binary chunks; mesh names cleaned for display (underscores removed, `_L`/`_R` written as Left/Right, a few source typos corrected); each mesh mapped by us to an FMA, UBERON or synthetic `HRA:` concept id (from the ontology ids in the GLB where present; `deploy/atlas/female/id_map.csv` lists every mapping and its source); display systems regrouped (adding "Reproductive (female)" and "Pregnancy reference") and colours added. Nothing is claimed about HuBMAP, NIH or DBCLS endorsing this interface.

This is a reference assembly with the whole-body skin surface and selected organs, including the female reproductive tract and breast. It is not a complete model of every human structure and not a female twin of BodyParts3D: the skeleton (91 structures: pelvis, lower limb, vertebrae) and muscles (16) are partial, there is no skull, rib cage or arm skeleton, and no vulva, clitoris or labia. Eight placenta and umbilical structures are classified under Pregnancy reference and hidden by default; they sit outside the body surface in the source file. Whether the model comes from one subject is not stated on the pages read; the interface does not claim it.

**Open licence check before the model is shown to users**: the Allen brain meshes' licence was known only second hand when the PRD was written. Either confirm it on the HRA dataset page, or build without them (`FEMALE_ARGS="--exclude-allen"`, see `deploy/atlas/female/README.md`).

## Historical assets (superseded)

Earlier repository revisions included female reference anatomy from the same HRA dataset (listed as *3D Reference Organ Set for Female v1.5 (2023)*). The current conversion is documented above; the earlier conversion is not part of this release.
