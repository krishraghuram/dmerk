import json
import pathlib
import collections.abc
import datetime
import random
import string

import dmerk.generate as generate


def path_to_str(obj):
    """
    Convert all pathlib.PurePath instances in obj to absolute path strings
    This is generic, in the sense that obj can be any python object, and not necessarily a merkle tree dictionary.
    """
    # Python 3.9 Compat
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, collections.abc.Mapping):
        return {path_to_str(k): path_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, collections.abc.Iterable):
        return [path_to_str(i) for i in obj]
    elif isinstance(obj, pathlib.PurePath):
        return repr(obj.resolve())
    else:
        raise TypeError(f"Can't handle type: {type(obj)}")


def str_to_path(obj):
    """
    Convert's all strings that begin with "PosixPath" or "WindowsPath" to pathlib.Path instances
    TODO: since we are using eval here, maybe we should probably use hmac to sign the output file, and verify signature while loading
    """
    PosixPath = pathlib.PosixPath
    WindowsPath = pathlib.WindowsPath
    if isinstance(obj, str):
        if obj.startswith("PosixPath") or obj.startswith("WindowsPath"):
            return eval(obj)
        else:
            return obj
    elif isinstance(obj, collections.abc.Mapping):
        return {str_to_path(k): str_to_path(v) for k, v in obj.items()}
    elif isinstance(obj, collections.abc.Iterable):
        return [str_to_path(i) for i in obj]
    # Python 3.9 Compat
    elif isinstance(obj, (int, float, bool, type(None))):
        return obj
    else:
        raise TypeError(f"Can't handle type: {type(obj)}")


def dump(obj, fp):
    json.dump(
        path_to_str(obj),
        fp,
        ensure_ascii=False,
    )


def dumps(obj):
    return json.dumps(
        path_to_str(obj),
        ensure_ascii=False,
    )


def load(fp):
    return str_to_path(json.load(fp))


def loads(s):
    return str_to_path(json.loads(s))


def _get_filename(path):
    filename_path = pathlib.Path(f"{path.name}.dmerk")
    while filename_path.exists():
        random_hex_string = "".join(random.choices(string.hexdigits.lower(), k=8))
        filename_path = pathlib.Path(f"{path.name}_{random_hex_string}.dmerk")
    return filename_path.name


def save_merkle(path, merkle, filename=None):
    if filename is None:
        filename = _get_filename(path)
    with open(filename, mode="w", encoding="utf-8") as file:
        output = {
            "_created": f"{datetime.datetime.now().isoformat(timespec='seconds')}",
            "_path": str(path.resolve()),
            "_merkle": merkle,
        }
        dump(output, file)
    print(f"Saved merkle for path: '{path}' to file: '{filename}'")


def load_merkle(filename):
    with open(filename, mode="r", encoding="utf-8") as file:
        return load(file)["_merkle"]


def generate_or_load(path, no_save=False):
    """
    Return merkle tree from path
    If path is a directory, generate "directory merkle tree" at path and return it
    If path is a file, load the "directory merkle tree" from the saved json file, and return it.
    """
    if isinstance(path, str):
        path = pathlib.Path(path)
    if path.is_dir():
        merkle = generate.generate(path)
        if not no_save:
            save_merkle(path, merkle)
        return merkle
    elif path.is_file():
        return load_merkle(path)
