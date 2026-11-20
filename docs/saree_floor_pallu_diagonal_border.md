# Floor pallu, diagonal border and cloth-only pleats — 20 November 2026

## Evidence available

The newest saved report remains `2026-11-20_111805_001`. Reviewed newer Desktop
tester outputs directly: `generated_3225.jpg` (11:37, floral folded-cloth detail)
and `generated_3232.jpg` (11:42, blue patterned cloth on a mannequin), plus catalog
`generated_3233.png`. The blue source appearance is visible in the delivered
full-product photo `generated_3230.png`. That is not the original uploaded file
or its request metadata, so these are visual comparisons, not a controlled test
establishing why the provider chose a mannequin.

## Changes

- Back reference pallu now reaches the floor and covers the rear skirt; no second
  skirt hem below it. Prompt agrees with the new reference. Back identity remains
  forbidden at definition, runner and provider levels. No separate face/person
  image is added, and the normal single-image Saree poses are untouched.
- Border uses a uniform-scale affine rotation of real source pixels. The selected
  band runs from corner 1 (top left) to corner 3 (bottom right); adjacent cloth is
  taken from the same source. Uncovered scene uses neutral grey, no decorative
  design is invented. Explicit border selection wins. Existing selection and
  reference-context logic stays unchanged so the working side view is unaffected.
  Automatic selection remains heuristic and may need an explicit crop.
- Pleats reference is a plain, tightly cropped folded textile, with the original
  printed stripes removed. Its left fan, right hanging panel and lower hem remain.
- Pleats now owns a cloth-only conditioning function. Previously the shared
  function prepended whole-saree colour text for single-colour-family inputs and
  omitted it for many multicolour inputs. This is a verified input-dependent code
  branch, not proof it was the sole cause of the observed mannequin. Removed that
  branch from this detail shot: every fabric starts with the same image-0 edit
  task; palette samples and material descriptions follow it and describe only the
  cloth. No whole-outfit construction prompt is inserted. Front, side, fourth
  product-photo shot and other garment prompts are unchanged.

No paid Cloudflare generation/upload was performed. New references and real-source
diagonal previews were visually reviewed. Regression checks cover diagonal corner
alignment, actual pixel colour, material/fabric variants and rear identity errors.
Offline tests do not establish live provider adherence for blue cloth or back.
Full offline suite: 181 tests passed. After final isolation cleanup, 44 targeted
tests passed. Front/side config equality was checked on two different fabrics.

## Reference edit provenance and prompt set

Built-in imagegen used; native PNGs copied into the project and hashes updated.

### Floor-length back — `03_back_view.png`

Generated file: `exec-41e16f93-c0ce-483c-ae0b-34d34d540377.png`.

Use case: precise-object-edit. Edit the rear-view saree catalog reference.
Preserve the same one adult woman, same rear-facing head and torso, bun hairstyle,
opaque plain ivory blouse, arm positions, left-hand grip, right hand, neutral
studio background, full head-to-floor framing and natural proportions. Change
ONLY the lower length and coverage of the PALLU draped from her left shoulder:
extend that existing broad continuous plain ivory pallu all the way down to the
FLOOR, with its bottom edge resting lightly at floor level and a tiny natural
settling fold, not a large train. Widen the lower pallu naturally enough that it
covers the wrapped skirt behind it from the held outer left edge to the right
side of her lower legs. The entire lower rear garment visible below the waist
reads as ONE continuous hanging pallu sheet. The shorter skirt hem MUST NOT
project below it and MUST NOT form a second visible lower tier, double hem,
second drape or separate panel. Keep the existing diagonal upper drape and hand
grip, with gravity-led soft vertical folds in the extended lower cloth. Preserve
modest opaque coverage. Do not change the rear wearer, no second person or second
head. The saree, pallu and blouse remain completely plain unpatterned ivory woven
cloth, with NO black lines, stripes, contrasting piping, printed borders or
motifs. Show the complete floor-touching pallu edge inside the frame with a small
amount of studio floor below. Soft diffuse neutral white light, no text or
collage. Same narrow portrait approximately 540:1224 aspect ratio. No separate
face or identity reference.

### Plain folded textile — `06_pleats_hem.png`

Generated file: `exec-e3b1e2f1-fea0-4562-adc1-7faa81355168.png`.

Use case: precise-object-edit. Edit this EXISTING close-up photograph of folded
saree fabric. Preserve its exact composition and natural 3D folds: the fan of
vertical skirt pleats on the left, diagonal overlapping cloth entering from the
upper left, straight hanging pallu panel on the right ending around the
lower-middle of the image, and the entire scalloped floor-level hem near the
bottom. Keep the same tight crop consisting only of cloth, same overlap
boundaries, fold count, realistic fold shadows, cloth thickness and small neutral
grey studio floor visible below the hem. There are NO visible people, plastic
mannequins, torso, neck, head, arms, hands or blouse in this photograph; do not
add any. Change ONLY the original textile markings: remove ALL BLACK DOUBLE
STRIPES, decorative bands and dark piping from the diagonal edge, vertical panel
edge, hanging panel lower edge and pleated bottom hem. Replace markings with
plain continuous ivory woven fabric matching adjacent cloth. Preserve the
physical folded edges and tone-on-tone stitched hem. All cloth is plain
unpatterned opaque ivory cotton with subtle realistic weave, NO printed lines or
ornamental borders anywhere. Neutral diffuse studio white light. Retain the
original tall close-up aspect approximately 320:514; this is a folded-textile
detail photograph, not a full garment/product mannequin view. No text, collage,
graphics or new objects.
