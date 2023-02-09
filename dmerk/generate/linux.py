import hashlib
import pathlib
import subprocess

_DIGEST_ALGORITHM = "md5" # md5 takes 10-20 percent less time to run than sha256
_FILE_DIGEST_LOOKUP_TABLE = None

def generate(directory: pathlib.Path):
    if (directory.exists()):
        global _FILE_DIGEST_LOOKUP_TABLE
        try:
            # ISSUE: https://github.com/krishraghuram/dmerk/issues/1
            allfiles = [p for p in directory.rglob("*") if p.is_file()]
        except PermissionError:
            # This occurs when we don't have execute permission on a directory,
            # since p.is_file() calls p.stat(), and that requires directory execute permission
            # More info on directory read and execute permissions here - https://unix.stackexchange.com/a/396071/420985
            raise
        _FILE_DIGEST_LOOKUP_TABLE = { pathlib.Path(k):v for k,v in _files_digest(allfiles).items() }
        return {
            directory: _merkle(directory)
        }
    else:
        raise NotADirectoryError(f"Directory '{directory}' does not exist")

def _files_digest(files):
    """
    Compute the digest of a list of files

    This creates a subprocess and runs GNU coreutils sha256sum to get the digest of all files
    It's better to do that than use hashlib because I'm pretty sure sha256sum would be faster

    Also, we fork a single process and get hashes of all files in the current directory,
    because that is much more performant than forking a subprocess for each file.
    """
    files = [f'"{str(file)}"' for file in files]
    ps = subprocess.run(["xargs", _DIGEST_ALGORITHM+"sum"], input=" ".join(files).encode("utf-8"), capture_output=True)
    err = ps.stderr.decode('utf-8')
    if err:
        # We are catching any and all errors from the subprocess here, but,
        # One known scenario is when we dont have read permissions on a file that we are trying to get digest for
        raise ChildProcessError(err)
    out = ps.stdout.decode('utf-8')
    lines = out.strip().split("\n")
    contents = {}
    for line in lines:
        digest,file = line.split(maxsplit=1)
        contents[file] = digest
    return contents

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
                "_digest": _FILE_DIGEST_LOOKUP_TABLE[child]
            }
    digest = _directory_digest(contents)
    return {
        "_type": "directory",
        "_digest": digest,
        "_children": contents,
    }

def _directory_digest(contents):
    """
    Compute the digest of a directory from the digests of its contents
    """
    digest_input = ",".join(list(sorted([v["_digest"] for v in contents.values()])))
    digest = hashlib.new(_DIGEST_ALGORITHM, digest_input.encode('utf-8')).hexdigest()
    return digest
