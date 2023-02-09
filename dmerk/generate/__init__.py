import pathlib
import subprocess
import hashlib

FILE_DIGEST_LOOKUP_TABLE = None
def generate(directory: pathlib.Path):
    if (directory.exists()):
        global FILE_DIGEST_LOOKUP_TABLE
        try:
            # ISSUE: https://github.com/krishraghuram/dmerk/issues/1
            allfiles = [p for p in directory.rglob("*") if p.is_file()]
        except PermissionError:
            # This occurs when we don't have execute permission on a directory,
            # since p.is_file() calls p.stat(), and that requires directory execute permission
            # More info on directory read and execute permissions here - https://unix.stackexchange.com/a/396071/420985
            raise
        FILE_DIGEST_LOOKUP_TABLE = { pathlib.Path(k):v for k,v in files_digest(allfiles).items() }
        return {
            directory: merkle(directory)
        }
    else:
        raise NotADirectoryError(f"Directory '{directory}' does not exist")

# Returns a dict with the following,
#   digest (of the entire directory)
#   dict containing all child paths and digests
def merkle(directory: pathlib.Path):
    children = [c for c in directory.iterdir()]
    for child in children:
        if (not (child.is_file() or child.is_dir())):
            raise ValueError(f"{child} is neither a file nor a directory")
    contents = {}
    for c in children:
        if (c.is_dir()):
            contents[c] = merkle(c)
        elif (c.is_file()):
            contents[c] = {
                "_type": "file",
                "_digest": FILE_DIGEST_LOOKUP_TABLE[c]
            }
    digest = directory_digest(contents)
    return {
        "_type": "directory",
        "_digest": digest,
        "_children": contents,
    }

# md5 takes 10-20 percent less time to run than sha256
_DIGEST_ALGORITHM = "md5"
_DIGEST_PROGRAM = _DIGEST_ALGORITHM+"sum"
_DIGEST_FUNCTION = getattr(hashlib, _DIGEST_ALGORITHM)

def files_digest(files):
    """
    Compute the digest of a list of files

    This creates a subprocess and runs GNU coreutils sha256sum to get the digest of all files
    It's better to do that than use hashlib because I'm pretty sure sha256sum would be faster

    Also, we fork a single process and get hashes of all files in the current directory,
    because that is much more performant than forking a subprocess for each file,
    like in below function file_digest(file)
    """
    files = [f'"{str(file)}"' for file in files]
    ps = subprocess.run(["xargs", _DIGEST_PROGRAM], input=" ".join(files).encode("utf-8"), capture_output=True)
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

def file_digest(file):
    """
    Compute the digest for a file
    """
    ps = subprocess.run([_DIGEST_PROGRAM, str(file)], capture_output=True)
    out = ps.stdout.decode('utf-8')
    digest = out.split()[0]
    return digest

def directory_digest(contents):
    """
    Compute the digest of a directory from the digests of its contents

    This is done within python, and we do not use GNU coreutils sha256sum, because the amout of data is very small
    """
    # # This is incorrect because it will include file paths, which means directories with same content but different path will lead to different hashes
    # digest_input = json.dumps(contents, sort_keys=True)
    # # Not using tuple because sha256 hash of tuple can't be verified from bash
    # # But if we use a string, we can create a file, fill it with a bunch of comma-separated hash digest,
    # # run it through sha256 program in bash, and verify that the output is same as python's hashlib.sha256
    # digest_input = tuple(sorted(contents.values()))
    # # Doesn't work, because each item in contents.values() will be a dict, some with just a digest, and some with a digest and contents
    # digest_input = ",".join(list(sorted(contents.values()["digest"])))
    digest_input = ",".join(list(sorted([v["_digest"] for v in contents.values()])))
    digest = _DIGEST_FUNCTION(digest_input.encode('utf-8')).hexdigest()
    return digest
