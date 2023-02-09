import hashlib
import pathlib

_DIGEST_ALGORITHM = "md5" # md5 takes 10-20 percent less time to run than sha256

def generate(directory: pathlib.Path):
    if (directory.exists()):
        return {directory:_merkle(directory)}
    else:
        raise NotADirectoryError(f"Directory '{directory}' does not exist")

# Returns a dict with the following,
#   digest (of the entire directory)
#   dict containing all child paths and digests
def _merkle(directory: pathlib.Path):
    children = [c for c in directory.iterdir()]
    for child in children:
        if (not (child.is_file() or child.is_dir())):
            raise ValueError(f"{child} is neither a file nor a directory")
    contents = {}
    for child in children:
        if (child.is_dir()):
            contents[child] = _merkle(child)
        elif (child.is_file()):
            contents[child] = {
                "_type": "file",
                "_digest": _file_digest(child)
            }
    digest = _directory_digest(contents)
    return {
        "_type": "directory",
        "_digest": digest,
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
    digest = hashlib.new(_DIGEST_ALGORITHM, digest_input.encode('utf-8')).hexdigest()
    return digest
