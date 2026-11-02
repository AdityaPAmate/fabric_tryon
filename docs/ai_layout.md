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

Three-quarter requests now ask for a front-dominant 30–45 degree view with both
shoulders, the front button line and one side seam visible. `back` retains its
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

Validation: 66 backend tests pass, including the moved shirt combination tests,
packaged-asset checks, source-template routing, framing contracts and independent
template generation after front rejection. Offline routing checks pass for all
24 garment/scenario combinations. Tester stream/report tests cover metadata.

The live velvet/face-reference catalog attempt at
`debug/catalog_references_velvet_20261102` stopped on the first Cloudflare request:
HTTP 429, code 4006, `allocation_exhausted`. No new image was generated and no
dependent calls were made. Thus new visual behavior is **not live-verified**.
After quota/account recovery, rerun `tools/test_catalog_live.py` with the desired
fabric, `--material velvet`, `--face-image PATH` and `--background white_marble_terrace`.
No deployment is implied by these source changes.
