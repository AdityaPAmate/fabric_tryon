# Saree full-side, template cleanup and pleats input correction

Reviewed saved report `2026-11-20_111805_001`, generated from a4bea2b. Request used
the floral/bird saree photo and Poonam identity, seed 42, white marble terrace.
No new paid Cloudflare requests or Cloudinary uploads were made for this fix.

## Findings and implementation

1. Back output retains black piping and sleeve stripes from the old blouse
   template, despite successful product transfer onto the saree. Edited the back
   reference to remove every original textile stripe from both blouse and saree,
   keeping the user's chosen rear pose, pallu silhouette and single wearer.
   Catalog back still forbids identity at declaration, execution and provider.
2. Side template was genuinely cropped above the lower body, and its prompt
   explicitly demanded the same half-length crop. Outpainted the same pose to
   a full head-to-floor reference with natural proportions and plain unmarked
   cloth. Updated shot framing and prompt to full length. Full source now supplies
   the actual terminal pallu artwork; a body-only product crop would hide it.
3. Border selector required saturated colour in >55% of rows. On sparse floral
   borders this selected only a small fragment. Compare sustained colour coverage
   against measured body coverage instead. The current floral photo selects the
   complete decorated side band; also visually checked the previous figure-print
   source. This is heuristic selection, not semantic certainty. Explicit crop
   remains authoritative, neutral/ambiguous designs may need user selection.
4. Pleats failed once with HTTP 400, provider code 3030, classified invalid input.
   Its extra border source crop was [281,0,312,740], only 31 pixels wide. The
   existing 511px input limit reduces that to 21 × 511. This is a verified
   malformed-reference risk; the provider's generic error does not prove its
   exact internal rejection condition. Additional border references now include
   enough adjacent genuine source cloth, preserving aspect and original pixels.
   Replaying those explicit bounds prepares 128 × 511, not 21 × 511. This is not
   a stretch/padding workaround and does not modify the user's display selection.
   Prepared input dimensions are recorded in diagnostics for future reports.

Fourth product photo, original front configuration, six-panel 3:4 layout, and
other garment configurations remain unchanged. No outer padding was added.
Normal single-image Saree pose assets remain separate.

## Reference provenance and exact edit prompt set

Built-in imagegen skill/tool used for these authorized reference replacements.
Native generated PNGs copied to catalog assets; manifest hashes/sizes updated.

### Full side: `02_three_quarter.png`

Generated source: `exec-c231ae0a-8062-4c86-b8fc-cbdaacb121a9.png`.

Use case: precise-object-edit / outpainting. Extend this existing saree catalog
side portrait DOWNWARD to make a natural FULL-LENGTH head-to-floor portrait. Keep
the same single adult woman, same head size relative to shoulders, same
three-quarter side-facing head and torso angle, same face, bun hairstyle,
earrings, gentle smile, skin, hands together at the waist, shoulder and blouse
silhouette. Do not compress or stretch her body. Preserve this upper pose and add
the missing natural lower body, long saree falling to the floor, realistic
vertical skirt pleats and a full floor-level hem, with a narrow area of studio
floor below. The woman has normal adult full-body proportions; not short, not
squat, not a giant head. Keep her head near the upper edge with small headroom,
not a huge empty top area. The pallu is long and naturally hangs from the forearm
down to lower-calf/ankle height alongside the skirt. This is a neutral
fabric-replacement template: REMOVE ALL black stripes, dark piping, horizontal
lines and decorative marks from BOTH the saree AND blouse, including the
shoulder, forearm edge, sleeves and lower hem. Use completely plain opaque
ivory/white woven fabric with realistic soft folds and plain finished edges
throughout. Do not add embroidery, texture prints, trim patterns or coloured
borders. One clean beige-grey studio backdrop, diffuse neutral white light, no
architecture, no props or text. Narrow full-length portrait with approximately
540:1164 aspect ratio. One woman only, fully inside the frame.

### Neutral back: `03_back_view.png`

Generated source: `exec-155ebca1-bce4-472e-8a19-407d306f8215.png`.

Use case: precise-object-edit. This existing single-woman REAR VIEW saree
photograph is the edit target. Preserve EXACTLY the existing one adult woman,
rear-facing head/torso, bun, modest opaque blouse shape and neckline, earrings,
arms, left hand grip, right hand, entire body proportions, crop, floor-level
skirt hem and the diagonal spread pallu silhouette. Do not add, remove, duplicate,
reposition or redesign the woman or fabric geometry. The ONLY change is to REMOVE
EVERY original textile design mark from BOTH the saree AND the blouse. Erase ALL
black parallel lines, stripes, dark piping at neckline, black lines on sleeves
and back blouse, horizontal black lines across the pallu, diagonal black border
lines, vertical black edge lines, double hem stripes and any other printed/dyed
marks. Replace those markings with continuous PLAIN IVORY WHITE woven cloth
matching its adjacent fabric, retaining the real seam shapes, cloth thickness,
folds, soft shading and physical edges. Blouse and saree are completely
unpatterned neutral ivory, with simple tone-on-tone stitching, no contrasting
piping, no new trim, no embroidery or patterns. Keep the full existing lower
skirt and pallu edge inside the portrait. Same neutral beige-grey studio backdrop,
soft diffuse neutral white light, no new scenery, text or graphics. Same narrow
portrait aspect, approximately 841:1870. No separate identity reference is
supplied or requested. Exactly ONE woman, exactly one head and one body.

## Verification scope

Both edited references visually inspected, including blouse/hem stripe removal
and complete side framing. Two distinct real source photos checked for the new
border crop. Regression tests exercise actual multipart bytes and dimensions
for the 31px crop, full-side source precedence, identity prohibition and existing
catalog behavior. Full suite and focused final checks recorded in ignored tmp
logs: final full suite passed 179 tests; focused checks passed 42 tests. No live
generated back/side/pleats success is claimed from these checks.
