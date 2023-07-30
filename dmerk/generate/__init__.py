import typing
from pathlib import Path

from ..merkle import Merkle
from .default import generate as default_generate


def generate(directory: Path) -> Merkle:
    # Can add platform-specific impl here if needed (for cross-platform compatibility or performance reasons)
    return default_generate(directory)
