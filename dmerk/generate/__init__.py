import logging
from pathlib import Path

from ..merkle import Merkle
from .default import generate as default_generate


def generate(directory: Path, continue_on_error: bool = False) -> Merkle:
    # Can add platform-specific impl here if needed (for cross-platform compatibility or performance reasons)
    logging.info(f"Generating merkle for path: '{directory}'")
    return default_generate(directory, continue_on_error)
