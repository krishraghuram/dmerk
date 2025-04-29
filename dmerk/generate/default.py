import hashlib
import logging
from pathlib import Path

from ..merkle import Merkle
from . import hashlib_file_digest

# hashlib.file_digest is only in python 3.11, we might need to backport/polyfill/monkey-patch if its not there
try:
    hashlib.file_digest  # type: ignore[attr-defined]
except AttributeError:
    hashlib.file_digest = hashlib_file_digest.file_digest  # type: ignore[attr-defined]

_DIGEST_ALGORITHM = "md5"  # takes 10-20 percent less time to run than sha256


def generate(directory: Path, continue_on_error: bool) -> Merkle:
    if directory.exists():
        return _generate(directory, continue_on_error)
    else:
        raise NotADirectoryError(f"Directory '{directory}' does not exist")


def _generate(directory: Path, continue_on_error: bool) -> Merkle:
    contents: dict[Path, Merkle] = {}
    for child in directory.iterdir():
        try:
            # is_symlink needs to be first because is_dir and is_file are True for symlinks
            if child.is_symlink():
                contents[child] = Merkle(
                    path=child,
                    type=Merkle.Type.SYMLINK,
                    # Python 3.9 Compat
                    size=child.lstat().st_size,
                    digest=_symlink_digest(child),
                )
            elif child.is_dir():
                contents[child] = _generate(child, continue_on_error)
            elif child.is_file():
                contents[child] = Merkle(
                    path=child,
                    type=Merkle.Type.FILE,
                    # Python 3.9 Compat
                    size=child.stat().st_size,
                    digest=_file_digest(child),
                )
            else:
                if continue_on_error:
                    # TODO: should we include special files in merkle output, so as to not lose information?
                    # We could just incl the file path, type and have size as 0, and digest as empty string ""
                    logging.error(f"{child} is neither a file nor a directory")
                    continue
                else:
                    raise ValueError(f"{child} is neither a file nor a directory")
        except (PermissionError, OSError) as e:
            if continue_on_error:
                logging.error(f"Error accessing {child}: {e}")
                continue
            else:
                raise
    return Merkle(
        path=directory,
        type=Merkle.Type.DIRECTORY,
        size=_directory_size(contents, directory),
        digest=_directory_digest(contents),
        children=contents,
    )


def _file_digest(file: Path) -> str:
    """
    Compute the digest for a file
    """
    with open(file, "rb") as f:
        digest: str = hashlib.file_digest(f, _DIGEST_ALGORITHM).hexdigest()  # type: ignore[attr-defined]
    return digest


def _symlink_digest(symlink: Path) -> str:
    """
    Compute the digest of a symlink
    """
    digest_input = str(symlink.readlink())
    digest = hashlib.new(_DIGEST_ALGORITHM, digest_input.encode("utf-8")).hexdigest()
    return digest


def _directory_digest(contents: dict[Path, Merkle]) -> str:
    """
    Compute the digest of a directory from the digests of its contents
    """
    digest_input = ",".join(list(sorted([v.digest for v in contents.values()])))
    digest = hashlib.new(_DIGEST_ALGORITHM, digest_input.encode("utf-8")).hexdigest()
    return digest


def _directory_size(contents: dict[Path, Merkle], directory: Path) -> int:
    """
    Compute the size of a directory from the contents
    """
    contents_total_size = sum([v.size for v in contents.values()])
    # Python 3.9 Compat
    return contents_total_size + directory.stat().st_size
