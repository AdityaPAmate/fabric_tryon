"""
Saree-only prompt route. Nothing in this package is used by any other
garment type. The only public entry point is build_saree_prompt().
"""

from .builder import build_saree_prompt

__all__ = ["build_saree_prompt"]