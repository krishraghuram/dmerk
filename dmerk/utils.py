import json
import pathlib
import collections.abc
import datetime

import dmerk.generate as generate

# TODO: better names for the functions here?


def flatten_merkle(merkle, prefix=None):
    """
    Reformat the merkle structure into a format similar to what `find` command on linux would output
    """
    if prefix:
        prefix = prefix + "/"
    else:
        prefix = ""
    flattened_merkle = {}
    for k, v in merkle.items():
        flattened_merkle[prefix + k] = v["_digest"]
        if v["_type"] == "directory":
            flattened_merkle |= flatten_merkle(v["_children"], prefix=prefix + k)
    return flattened_merkle


"""
The next few functions are a hack/workaround for the issue that
json.dumps cannot handle pathlib.Path instances when present in dict keys
The default/cls options of json.dumps also dont work, as those options only work on values, and not keys
https://stackoverflow.com/a/63455796/5530864
https://github.com/python/cpython/issues/63020

I really hate this hack for the following reasons:
1. The problem statement is quite simple, but the code is complicated - In other words, the code is not pythonic
2. format_merkle_paths re-creates a ton of dict's, and I am unsure of how badly it will pull-down the performance

But this is a hack I'm willing to live with until I figure out the "Right Thing To Do TM",
which could (or could not) be any one of,
* Custom JsonEncoder
* For saving-loading, use hmac+pickle, and for printing/saving (for human-readability) use json with the below hack.
"""


def path_to_str(obj):
    """
    Convert all pathlib.PurePath instances in obj to absolute path strings
    This is generic, in the sense that obj can be any python object, and not necessarily a merkle tree dictionary.
    """
    if isinstance(obj, collections.abc.Mapping):
        return {path_to_str(k): path_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, str):
        return obj
    elif isinstance(obj, collections.abc.Iterable):
        return [path_to_str(i) for i in obj]
    elif isinstance(obj, pathlib.PurePath):
        return str(obj.resolve())
    else:
        raise TypeError(f"Can't handle type: {type(obj)}")


def format_merkle_paths(merkle, formatter, formatter_updater):
    """
    Format paths in a merkle tree using the given formatter
    """
    new_merkle = {}
    for k, v in merkle.items():
        new_merkle[formatter(k)] = {
            "_type": v["_type"],
            "_digest": v["_digest"],
            "_size": v["_size"],
        }
        if v["_type"] == "directory":
            k = formatter(k)
            children = format_merkle_paths(
                v["_children"], formatter_updater(formatter, k, v), formatter_updater
            )
            new_merkle[k] |= {"_children": children}
    return new_merkle


def dump(merkle, file):
    def formatter(p):
        return str(p.resolve())

    def formatter_updater(formatter, k, v):
        def formatter(p):
            return p.name

        return formatter

    return json.dump(
        format_merkle_paths(merkle, formatter, formatter_updater),
        file,
        sort_keys=True,
        indent=4,
        ensure_ascii=False,
    )


def load(file):
    def formatter(p):
        return pathlib.Path(p)

    def formatter_updater(formatter, k, v):
        def formatter(p):
            return pathlib.Path(k) / p

        return formatter

    return format_merkle_paths(json.load(file), formatter, formatter_updater)


def _get_filename(path):
    date = datetime.datetime.now().isoformat(timespec="seconds").replace(":", "-")
    table = str.maketrans({"\\": "_", "/": "_", ":": "_"})
    return f"{date}__{str(path).translate(table)}.json"


def save_merkle(path, merkle, filename=None):
    if filename is None:
        filename = _get_filename(path)
    with open(filename, mode="w", encoding="utf-8") as file:
        dump(merkle, file)
    print(f"Saved merkle for path: '{path}' to file: '{filename}'")


def load_merkle(filename):
    with open(filename, mode="r", encoding="utf-8") as file:
        return load(file)


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
