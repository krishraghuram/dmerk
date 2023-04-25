import hashlib
import pathlib
import glob

_DIGEST_ALGORITHM = "md5"  # takes 10-20 percent less time to run than sha256

# hashlib.file_digest is only in python 3.11, we might need to backport/polyfill/monkey-patch if its not there
try:
    hashlib.file_digest
except AttributeError:
    from . import hashlib_file_digest

    hashlib.file_digest = hashlib_file_digest.file_digest


def generate(directory: pathlib.Path, *, exclude: list[str]):
    if directory.exists():
        paths_to_exclude = []
        for pattern in exclude:
            for match in glob.glob(pattern, root_dir=directory, recursive=True):
                paths_to_exclude.append(directory / pathlib.Path(match))
        return {directory: _merkle(directory, paths_to_exclude)}
    else:
        raise NotADirectoryError(f"Directory '{directory}' does not exist")


# Returns a dict with the following,
#   digest (of the entire directory)
#   dict containing all child paths and digests
def _merkle(directory: pathlib.Path, paths_to_exclude: list[pathlib.Path]):
    children = []
    for child in directory.iterdir():
        if not any([child.is_relative_to(i) for i in paths_to_exclude]):
            if not (child.is_symlink() or child.is_dir() or child.is_file()):
                raise ValueError(f"{child} is neither a file nor a directory")
            children.append(child)
    contents = {}
    for child in children:
        # is_symlink needs to be first because is_dir and is_file are True for symlinks
        if child.is_symlink():
            contents[child] = {
                "_type": "symlink",
                "_size": child.stat(follow_symlinks=False).st_size,
                "_digest": _symlink_digest(child),
            }
        elif child.is_dir():
            contents[child] = _merkle(child, paths_to_exclude)
        elif child.is_file():
            contents[child] = {
                "_type": "file",
                "_size": child.stat(follow_symlinks=False).st_size,
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


def _symlink_digest(symlink):
    """
    Compute the digest of a symlink
    """
    digest_input = str(symlink.readlink())
    digest = hashlib.new(_DIGEST_ALGORITHM, digest_input.encode("utf-8")).hexdigest()
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
    return contents_total_size + directory.stat(follow_symlinks=False).st_size
