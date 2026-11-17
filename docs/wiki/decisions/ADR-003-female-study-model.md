# ADR-003: Female study model as the default female atlas

| | |
|---|---|
| Date | 2026-11-17 |
| Status | **Accepted** on 2026-11-17: the user chose to replace the live female set with the human-atlas-enhanced "female study model v3". |
| Repo state | `main` @ `d3bd9fb` (before this change) |
| Evidence | [human-atlas-enhanced](../research/2026-11-16-human-atlas-enhanced.md) · [slorksmo/Human-Atlas](../research/2026-11-16-slorksmo-human-atlas.md) · [Female 3D model survey](../research/2026-11-15-female-anatomy-3d-models.md) |
| Install | [`deploy/atlas/female-study/README.md`](../../../deploy/atlas/female-study/README.md) (files, SHA-256, upstream commit `fb3ca0f`) |

## Context
The live Female view (behind the `female_atlas` flag) showed our build of the HRA Visible Human Female v1.5 organ set:
606 meshes, organs plus a partial skeleton and 16 muscles, 17.0 MB gzip. It has no whole body, so most of the male
viewer's teaching (bones, muscles, vessels in place) had no female counterpart.

The human-atlas-enhanced fork ships a "female study model v3" (by wiiiimm, 2026-09-07): 2,181 BodyParts3D 4.0 male
meshes reshaped to estimated female proportions by hand-tuned morph fields, plus 64 HRA VH_F v1.5 female meshes
(reproductive tract, breast, pelvis, two knee ligaments) fitted into that body. It is a whole body, in our chunk format,
with FMA ids on the reshaped parts. But 97% of its meshes are male anatomy; the upstream authors call the morphs
"artistic estimates" and the review unresolved. The research note recommended ignoring it for that reason.

## Decision
The user chose the study model as the default female body (2026-11-17), with the honesty measures below. The HRA
organs-only build stays in the pipeline as a non-default fallback (`FEMALE_MODEL=hra deploy/atlas/build_atlas.sh`).

## Alternatives considered
1. **Keep HRA VH_F v1.5 organs-only (status quo).** Native female data only, 17 MB, but no whole body, partial
   skeleton, no muscles. Rejected by the user in favour of a whole-body view.
2. **slorksmo/Human-Atlas female set** (HRA v1.10 + 76 Andreassen leg muscles + 180 fitted BodyParts3D bones). About
   double our size, keyed by `HRA:` slugs without FMA or UBERON ids (breaks our FMA deep links and crosswalk), about 15%
   male bones, a one-day unmaintained build, DOI not resolving. Not chosen.
3. **human-atlas-enhanced HRA reference (`atlas-female.json`)**: the same HRA v1.5 data we already had (888 parts with
   Allen brain). Nothing new. Not chosen.
4. **Female study model v3 (chosen).** Whole body, same chunk format and FMA ids, 35.1 MB gzip; male-derived.
5. **Other open female sources** (Z-Anatomy and others in the 2026-11-15 survey): share-alike or unclear female
   content, or licence unclear. Not suitable.

## Honesty measures (medical app)
- Toggle label **"Female (study model)"**; tooltip (`atlas.sex.female`): "A male-derived body reshaped to a female
  form, plus female organs from the Human Reference Atlas. Shows the female study model, for orientation only."
- One-line note under the toggle while Female is shown: "Female study model: a male body reshaped to a female form,
  with female organs from the Human Reference Atlas; for orientation only."
- Every part carries `origin` (`hra-female` | `bp3d-reshaped`) in `female.json`, from the upstream `provenance.source`.
  The selection panel shows "Reshaped from the male model (BodyParts3D), not female anatomy data." (or the HRA / mixed
  line) for every selection in the Female view.
- `/api/spatial/resolve` returns `origin`; a reshaped structure is never reported as `sex: "female"`. Female-only
  structures (uterus, ovaries, uterine tubes...) resolve to their HRA parts via `rag/female_study_origin.json`. FMA deep
  links of reshaped parts (`?select=FMA9611&sex=female`) keep working; answer links still come only from reviewed
  crosswalk rows.
- Credits: `deploy/atlas/ATTRIBUTION.md`, `/credits` and `apps/web/THIRD_PARTY_NOTICES.md` credit BodyParts3D (CC BY 4.0,
  reshaped by the fork's morph fields), HRA VH_F v1.5 (CC BY 4.0) and the fork (MIT), and list our changes.
- Not included, and said so in the credits: vulva, clitoris, labia, female urethra, female pelvic floor.

## Consequences
- Female download grows from 17.0 MB to 35.1 MB gzip (measured 35.4 MB transferred incl. manifest, local QA
  2026-11-17). The confirm sheet already shows the size before download.
- The browser cache key changes (`version` `female-study-v3@fb3ca0f`), so users re-download once.
- Rollback: `FEMALE_MODEL=hra` build and push, and revert the UI copy, or the labels describe the wrong model.
