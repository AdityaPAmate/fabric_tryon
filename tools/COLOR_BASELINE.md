# Colour baseline, stages 1 and 2

Run `capture_color_baseline.py` from the repository root with `--fabric-dir`,
`--files` and a new `--output debug/...` directory. This calls the production
resize function directly, reads the engine's actual size constant, and makes
no network requests. Optional `--crop-box left upper right lower` reproduces a
known crop. Omitted means no crop; historical crop settings are unknown.

The manifest stores source hashes, source code snapshots, commit, dimensions,
ICC presence, RGB averages, HSV saturation averages and JPEG error. Originals,
lossless resized references and exact prepared JPEG bytes are saved separately.
`comparison.png` displays both at comparable viewing size. Source snapshots
exclude project settings and environment files.

Compare original vs lossless resized saturation to examine spatial averaging;
compare lossless resized vs JPEG to examine encoding losses. Whole-image mean
RGB is not a test of local print fidelity or perceived colour accuracy. Pattern
mixing during downsampling can lower saturation even with unchanged RGB means.
ICC presence is recorded only; this audit does not perform profile conversion.

The verified run is `debug/color_baseline_20261031_verified`. The attached
blue-flower swatch matches `kurti_fabric3.png` byte-for-byte, not the files named
floral. Red velvet is `red_velvet7.jpg`. Three historical user-provided outputs
are archived in `historical_outputs/`; request settings and deployed revision
are unknown. They are visual references, not controlled before/after runs.

Stage 1 is an offline audit of current local processing, not evidence of the
bytes sent by the historical deployment. Stage 2 has an archived evidence
baseline, but a controlled generation baseline still needs a saved complete
request: person image, fabric image, garment/style, pose, camera, background,
details, note, options/crop, seed, guidance, model identifier, actual prompt,
effective seed/retry trace and output. Unknown fields must remain unknown.
Do not use garment-wide image averages to compare with a swatch; first select
comparable garment regions excluding skin/background, shadows and highlights.

No generation prompts or image processing behaviour are modified by this tool.

## Controlled generation baseline

`generate_color_baseline.py` uses the project virtualenv and existing `.env`.
`--prepare-only` saves the complete ten-case plan without network access.
Omit that switch to execute the plan only after permission to send the face
reference and fabrics to Cloudflare. No Cloudinary upload is performed.

Prepared run: `debug/generation_baseline_20261031/baseline.json`.
Five fabrics: blue floral/cream, red velvet, plain green, faint purple, blue
checks. Each has a neutral studio and white marble terrace case. This sample
does not contain a pure white swatch and is not an exhaustive fabric benchmark.
One face reference (`person20_face.png`), generated trim male body, business
blazer, front view, seed 42, guidance 7, final-size output (1536 px long side).
The face-photo route allows studio/outdoor backgrounds without modifying the
application's prompts or inventing an unsupported neutral-background option.
It does not test preservation of the person's full photographed body shape.

Each case stores originals, exact prepared provider inputs, prompt config and
request. Executed attempts additionally save actual submitted prompts/settings,
input hashes, statuses and effective seed, including fallback attempts. A
fallback with another seed/prompt must be distinguished during comparisons.
Successful output bytes and their hashes are retained and not regenerated on
resume. The manifest verifies source and input hashes before resume.

Current state: user explicitly approved sending the face and fabrics to
Cloudflare. All ten outputs were generated, visually reviewed, and verified
at 1152 x 1536. Output hashes, successful request seeds and actual submitted
input hashes were checked. See `debug/generation_baseline_20261031/index.html`
for the comparison gallery and `baseline.json` for the complete provenance.

Outdoor velvet, green and purple required the engine's existing fallback,
which changed seed 42 to 43 and used its compact fallback prompt. These are
valid per-case regression references but not controlled background-only pairs.
Future comparisons must use the successful attempt's exact prompt and seed.
Floral and checks succeeded with seed 42 in both scenes. One sample per case
does not establish provider repeatability or isolate a causal lighting effect.

Visual review: faint purple shifts strongly towards grey; fine checks lose
visibility; floral print appears muted; velvet colour/surface appearance
differs from the swatch. These are qualitative observations, not measured
garment-region colour errors. Face identity also drifts in the generated
images, so these outputs do not establish face preservation quality.
Stage 2's five-fabric, two-scene baseline is captured. No production prompts,
lighting instructions, colour corrections or material parameters were changed.
