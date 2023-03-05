import hashlib
import pathlib

_DIGEST_ALGORITHM = "md5"  # takes 10-20 percent less time to run than sha256

# hashlib.file_digest is only in python 3.11, we might need to backport/polyfill/monkey-patch if its not there
try:
    hashlib.file_digest
except AttributeError:
    from . import hashlib_file_digest

    hashlib.file_digest = hashlib_file_digest.file_digest


def generate(directory: pathlib.Path):
    if directory.exists():
        return {directory: _merkle(directory)}
    else:
        raise NotADirectoryError(f"Directory '{directory}' does not exist")


# Returns a dict with the following,
#   digest (of the entire directory)
#   dict containing all child paths and digests
def _merkle(directory: pathlib.Path):
    children = [c for c in directory.iterdir()]
    for child in children:
        if not (child.is_file() or child.is_dir()):
            raise ValueError(f"{child} is neither a file nor a directory")
    contents = {}
    for child in children:
        if child.is_dir():
            contents[child] = _merkle(child)
        elif child.is_file():
            contents[child] = {
                "_type": "file",
                "_size": child.stat().st_size,
                "_digest": _file_digest(child),
            }
    return {
        "_type": "directory",
        "_size": _directory_size(contents, directory),
        "_digest": _directory_digest(contents),
        "_children": contents,
    }


def _file_digest(file):
    """
    Compute the digest for a file
    """
    with open(file, "rb") as f:
        digest = hashlib.file_digest(f, _DIGEST_ALGORITHM).hexdigest()
    return digest


def _directory_digest(contents):
    """
    Compute the digest of a directory from the digests of its contents
    """
    digest_input = ",".join(list(sorted([v["_digest"] for v in contents.values()])))
    digest = hashlib.new(_DIGEST_ALGORITHM, digest_input.encode("utf-8")).hexdigest()
    return digest


def _directory_size(contents, directory):
    """
    Compute the size of a directory from the contents
    """
    contents_total_size = sum([v["_size"] for v in contents.values()])
    return contents_total_size + directory.stat().st_size
