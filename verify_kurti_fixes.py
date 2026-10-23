"""Offline route/settings verification for the garment prompt architecture.

Run from the project root: python verify_kurti_fixes.py
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("check_pose_prompts.py")), run_name="__main__")
