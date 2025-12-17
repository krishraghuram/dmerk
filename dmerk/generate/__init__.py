import logging
from pathlib import Path

from ..merkle import Merkle
from .default import generate as default_generate
from .default import _directory_digest, _directory_size, PathT

# Can add platform-specific implementations here if needed
# (for cross-platform compatibility or performance reasons)


def generate(directory: Path, fail_on_error: bool = False) -> Merkle:
    logging.info(f"Generating merkle for path: '{directory}'")
    return default_generate(directory, fail_on_error)


def directory_size(contents: dict[PathT, Merkle], directory: Path) -> int:
    return _directory_size(contents, directory)


def directory_digest(contents: dict[PathT, Merkle]) -> str:
    return _directory_digest(contents)
