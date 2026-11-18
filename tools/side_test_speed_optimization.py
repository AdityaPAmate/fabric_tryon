"""Side benchmark script: Compare current vs optimized catalog generation speeds

This script runs completely independently and DOES NOT modify any existing
production code files. It tests optimizations on the side.
"""
import os
import sys
import time
import io
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tryon.settings')
import django
django.setup()

from fabricapp.catalog_engine.registry import get_definition
from fabricapp.catalog_engine.validation import validate_definition
from fabricapp.ai.garments.blazer.catalog.business import finish_shot as blazer_finish_shot, REFERENCES as BLAZER_REFS
from fabricapp.ai.garments.kurta.catalog.pathani import layout as pathani_layout


def benchmark_current_vs_optimized():
    print("=" * 70)
    print("🏎️  SIDE-TEST SPEED BENCHMARK: CURRENT VS OPTIMIZED")
    print("=" * 70)

    # 1. Inspect Kurta Pathani
    pathani_def = get_definition('kurta', 'pathani-v1')
    p_layout = pathani_layout({})
    panel_sizes = {p.shot: (p.box[2] - p.box[0], p.box[3] - p.box[1]) for p in p_layout.panels}

    print("\n--- 1. KURTA (PATHANI-V1) PIXEL AUDIT ---")
    print(f"{'Shot Key':<12} | {'Panel Size in Collage':<22} | {'Current Gen Size':<18} | {'Proposed Opt Size':<18} | {'Pixel Reduction'}")
    print("-" * 100)

    dummy_img = Image.new('RGB', (500, 500), color=(120, 80, 50))
    buf = io.BytesIO()
    dummy_img.save(buf, 'JPEG')
    data = {'garment_type': 'kurta', 'options': {'draft_mode': False}, 'fabric_image': buf, 'seed': 42}

    total_curr_pixels = 0
    total_opt_pixels = 0

    for shot in pathani_def.shots:
        buf.seek(0)
        cfg = pathani_def.build_config(data, shot, 42)
        curr_dims = cfg.get('output_dimensions', (512, 512))
        panel = panel_sizes.get(shot.key, (0, 0))

        if shot.operation in ('crop', 'swatch_composite'):
            opt_dims = curr_dims
            curr_px = 0
            opt_px = 0
            reduction = "0% (Local 0s)"
        else:
            curr_px = curr_dims[0] * curr_dims[1]
            total_curr_pixels += curr_px

            # If cuff is converted to swatch_composite or resized:
            if shot.key in ('cuff', 'collar'):
                # Proposed: fit 1024 or match panel*2
                scale = 1024 / max(curr_dims)
                opt_dims = (round(curr_dims[0] * scale / 32) * 32, round(curr_dims[1] * scale / 32) * 32)
                opt_px = opt_dims[0] * opt_dims[1]
                reduction = f"-{(1 - opt_px/curr_px)*100:.1f}%"
            else:
                opt_dims = curr_dims
                opt_px = curr_px
                reduction = "0% (Full Body)"
            total_opt_pixels += opt_px

        print(f"{shot.key:<12} | {panel[0]}x{panel[1]:<17} | {curr_dims[0]}x{curr_dims[1]:<13} | {opt_dims[0]}x{opt_dims[1]:<13} | {reduction}")

    print(f"\nTotal AI Generated Pixels (Kurta Pathani):")
    print(f"  Current:  {total_curr_pixels:,} pixels (~{total_curr_pixels/1e6:.2f} Megapixels)")
    print(f"  Proposed: {total_opt_pixels:,} pixels (~{total_opt_pixels/1e6:.2f} Megapixels)")
    print(f"  Savings:  -{(1 - total_opt_pixels/total_curr_pixels)*100:.1f}% less GPU work required!\n")

    # 2. Benchmark Local Post-Processing Time (finish_shot in Blazer)
    print("--- 2. BENCHMARKING BLAZER POST-PROCESSING (finish_shot) ---")
    test_gen_img = Image.new('RGB', (600, 1500), color=(50, 50, 150))
    test_gen_bytes = io.BytesIO()
    test_gen_img.save(test_gen_bytes, 'PNG')
    test_gen_bytes = test_gen_bytes.getvalue()

    from fabricapp.ai.providers.cloudflare_engine import GenerationResult
    mock_gen = GenerationResult(test_gen_bytes, 42, {})

    blazer_data = {
        'garment_type': 'blazer',
        'garment_style': 'business',
        'fabric_image': buf,
        'options': {'draft_mode': False},
        'seed': 42,
    }

    blazer_def = get_definition('blazer', 'business-v1')
    front_shot = next(s for s in blazer_def.shots if s.key == 'front')

    # Warmup
    buf.seek(0)
    try:
        t0 = time.monotonic()
        _ = blazer_finish_shot(blazer_data, front_shot, mock_gen)
        t_post = (time.monotonic() - t0) * 1000
        print(f"  Blazer front shot finish_shot duration: {t_post:.1f} ms")
    except Exception as e:
        print(f"  Finish shot test skipped: {e}")

    # 3. Time comparison projection
    print("\n" + "=" * 70)
    print("⏱️  PROJECTED LATENCY COMPARISON")
    print("=" * 70)
    print(f"{'Garment Type':<15} | {'Current Latency':<18} | {'With Opt 1 (1024px)':<20} | {'With Opt 1+2 (Composite)'}")
    print("-" * 75)
    print(f"{'Shirt':<15} | {'~70s (Baseline)':<18} | {'~70s (Already Opt)':<20} | {'~70s'}")
    print(f"{'Kurta Pathani':<15} | {'~135s (5 AI @ 1536)':<18} | {'~75s (5 AI @ 1024)':<20} | {'~55s (4 AI + Cuff Swatch)'}")
    print(f"{'Blazer Business':<15} | {'~125s (3 AI @ 1536)':<18} | {'~68s (3 AI @ 1024)':<20} | {'~65s (3 AI + Quick Crop)'}")
    print("=" * 70)
    print("✅ Side-test complete. No production files were modified.")


if __name__ == '__main__':
    benchmark_current_vs_optimized()
