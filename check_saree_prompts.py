"""Run the focused saree prompt regression suite.

Run from the project root: python check_saree_prompts.py
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("check_saree_regressions.py")), run_name="__main__")
