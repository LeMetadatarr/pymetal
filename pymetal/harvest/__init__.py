"""Bulk (catalogue-wide) harvesters for pymetal, built on the shared harvestkit engine.

This is an opt-in extra (``pip install pymetal[harvest]``). Importing this
package registers the available sources with harvestkit's registry.
"""
from __future__ import annotations

from pymetal.harvest import bands  # noqa: F401  (import registers MetalArchivesSource)


def main() -> int:
    """Console-script entry point: ``pymetal-harvest``."""
    from harvestkit.engine import run_cli

    from pymetal.harvest.bands import MetalArchivesSource

    return run_cli(MetalArchivesSource)
