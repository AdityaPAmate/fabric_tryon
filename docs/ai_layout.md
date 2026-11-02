# AI code layout

The public entry point remains `fabricapp.ai.main.generate_tryon_image`.
HTTP endpoint paths and request fields are unchanged. Internal imports now use
the packages below; code using old internal module paths must update imports.

- `pipeline/`: garment routing, shared scenario composition and catalog shot prompts.
- `fabric/`: measured swatch colours, material instructions and shared conditioning.
- `scene/`: background descriptions and camera framing.
- `references/`: face/pose/catalog reference lookup; bundled images under `assets/`.
- `images/`: image resizing, crop and output-size helpers.
- `providers/`: Cloudflare requests, error classification and image integrity checks.
- `garments/`: ready-garment adapter, detail engine and the six garment packages.
- `diagnostics/`: optional debug image copies.

Each garment owns its builder, prompts, details, poses and generation settings.
Blazer's framing/retry/material compatibility/experimental lighting modules stay
inside its garment package. Root `ai/` contains only `main.py` and `__init__.py`.

Six commented legacy modules moved to `docs/legacy_ai/`; they are not runtime
imports. The shirt prompt-combination tests moved to
`fabricapp/test_shirt_prompt_combinations.py`, alongside the existing test modules
(`fabricapp/tests.py` already exists, so no conflicting `tests` package was added).

Reference files resolve relative to their Python module, including face and saree
pose assets. They no longer depend on launching the process from the project root.
Dynamic garment module names, tests, diagnostic scripts and developer tools use
the new package locations.

## Catalog references and framing

The user-provided `shirt_collar.png` and `sleeve.png` are bundled unchanged under
`references/assets/catalog/shirt/`. Shirt `collar` and `cuff` catalog shots edit
these photos directly, replacing all visible shirt fabric with the submitted
swatch. Geometry, buttons, skin, crop and background come from the template;
these are fabric-detail templates, not identity-matched photos of the customer.
No uploaded face photo is used as the template subject. Other details retain the
front-output reference. The templates can still run if the front is rejected,
unless a quota/auth failure prevents all generation.

Three-quarter requests now ask for a clear 45-degree front-and-side view with
an offset button line and foreshortened far shoulder. That shot uses a blank
canvas and the approved front image as image 2, rather than editing the original
front pose in place. `back` retains its
API key but now requests a rear garment close-up; shirts are cropped from
shoulders to hem, excluding legs/shoes. Trousers use waistband-to-hem framing.
View prompts explicitly retain the selected background and put framing last,
after material instructions. Template shots retain the template background.
Images include `framing` and `reference_template` metadata, retained in tester
reports together with seeds and provider diagnostics.

## Report findings and limits

Four shirt catalog reports dated 2026-11-02 were reviewed locally. One contained
an asymmetric half-tucked shirt, one lost its terrace background in the angle
view, and one used the face-reference photo's room as the generated setting.
The red velvet input report selected `fabric_type=silk`; this is not evidence of
the explicit velvet mode failing. User-selected material remains authoritative.
No automatic fabric-type guessing was added.

Shirt prompts now separate face identity from the source crop/clothing/scene,
reinforce symmetric tucked/untucked construction and requested framing, and
retain those rules for every material and retry prompt. Velvet describes visible
short pile and broad diffuse highlights rather than smooth satin-like glare.
Colour measurement/conditioning behavior is retained; colour mismatch remains
unresolved and further colour work is deferred at the user's request.

Validation: 67 backend tests pass, including the moved shirt combination tests,
packaged-asset checks, source-template routing, framing contracts and independent
template generation after front rejection. Offline routing checks pass for all
24 garment/scenario combinations. Tester stream/report tests cover metadata.

The live velvet/face-reference catalog attempt at
`debug/catalog_references_velvet_20261102` stopped on the first Cloudflare request:
HTTP 429, code 4006, `allocation_exhausted`. No new image was generated and no
dependent calls were made. This initial quota blocker was resolved after the
user updated their account; live follow-up results are recorded below.
To repeat the check, run `tools/test_catalog_live.py` with the desired
fabric, `--material velvet`, `--face-image PATH` and `--background white_marble_terrace`.
No deployment is implied by these source changes.

## Live follow-up after quota recovery (2026-11-02)

All work continues on `codex/organized-ai-catalog-references`; the user requested
reusing the current branch for subsequent pushes rather than creating a branch
for every push.

- `debug/catalog_quota_recheck_20261102`: red velvet, uploaded face reference and
  marble terrace, one real multipart request. Five views generated/uploaded.
  Collar failed strict output-size validation (not moderation): 1536 x 1256 was
  requested and the returned image had different dimensions. The angle remained
  too frontal. Front showed a complete, untucked shirt with visibly plush velvet;
  back was a rear upper-body close-up retaining the terrace setting.
- Template requests now align their requested dimensions to multiples of 32;
  this is limited to template configs. Ordinary requests retain prior sizing and
  strict output-integrity validation is unchanged. No returned image is stretched
  or accepted with mismatched dimensions.
- `debug/catalog_targeted_recheck_20261102`: two successful real generation and
  upload calls, including collar at 1536 x 1248 and the new angle reference route.
- `debug/catalog_pattern_final_20261102`: a checked fabric with cotton selection,
  uploaded face and terrace; all six images generated/uploaded from one multipart
  request. Visual review found that angle rotation was still weak, and the cuff
  template preserved the torso's white cloth behind the arm.
- `debug/catalog_angle_cuff_final_20261102`: two successful focused live rechecks
  after a compact camera prompt and explicit torso-region replacement instruction.
  Angle is visibly oblique while retaining the terrace and complete shirt. The
  torso behind the cuff now largely receives the pattern; a small light region
  remains near the fabric boundaries. This is not perfect semantic segmentation.

Sixteen generation calls were made across the four runs: fifteen produced valid,
uploaded images and the initial collar failed validation. Focused runs reused the
saved front anchor rather than regenerating the person. Both velvet and patterned
fabric were visually reviewed. Pattern scale, exact physical colour, tiny boundary
regions and consistent camera angles across arbitrary inputs remain limitations;
no automatic quality classifier or claim of exhaustive garment coverage is added.
