import hashlib
import json
import random
import pathlib
import sys

import pytest

from ...generate import default_generate
from ... import utils
from ..conftest import update_metadata, assert_merkle

generates = [default_generate]


@pytest.mark.parametrize("generate_function", generates)
@pytest.mark.parametrize(
    "fs",
    [
        {"dmerk_tests": {"dir1": {"file1": "Hello World 1", "file2": "Hello World 2"}}},
        {"dmerk_tests": {"dir1": {}}},  # Empty dir
        {
            "dmerk_tests": {
                ".dir1": {".file1": "Hello World 1", ".file2": "Hello World 2"}
            }
        },  # Hidden Files
        # TODO: '\t' breaks tests in windows, need to find a way to fix this test-case
        # {"dmerk_tests":{"Dir 1":{"File 1":"Hello World 1","'\tF i l e 2\t'":"Hello World 2"}}}, # Whitespace in Filenames
        {
            "dmerk_tests": {"📁1": {"ファイル一": "こんにちは世界 一", "ファイル二": "こんにちは世界 二"}}
        },  # Unicode outside Basic Latin block
    ],
    indirect=True,
)
def test_digest_correct(generate_function, fs, request):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    print(f"With data:\n{json.dumps(fs.sourcedata, indent=4)}")
    m1 = generate_function(fs.basepath)
    print("Merkle Digest:")
    utils.dump(m1, sys.stdout)
    print()
    digest = lambda s: (getattr(hashlib, "md5")(s.encode("utf-8")).hexdigest())

    def get_merkle_tree_test(data, prefix=None):
        if prefix is None:
            prefix = pathlib.Path(".")
        out = {}
        for k, v in data.items():
            if isinstance(v, str):
                out[prefix / pathlib.Path(k)] = {"_type": "file", "_digest": digest(v)}
            elif isinstance(v, dict):
                children = get_merkle_tree_test(v, prefix=prefix / k)
                out[prefix / pathlib.Path(k)] = {
                    "_type": "directory",
                    "_digest": digest(
                        ",".join(sorted([v["_digest"] for v in children.values()]))
                    ),
                    "_children": children,
                }
        return out

    m2 = get_merkle_tree_test({fs.basepath: fs.sourcedata})
    print("Computed Merkle Digest:")
    utils.dump(m2, sys.stdout)
    print()
    assert m1 == m2


@pytest.mark.parametrize("generate_function", generates)
@pytest.mark.parametrize(
    "fs",
    [
        {"dmerk_tests": {"file1": "Hello World 1", "file2": "Hello World 2"}},
        {"dmerk_tests": {"dir1": {"file1": "Hello World 1", "file2": "Hello World 2"}}},
    ],
    indirect=True,
)
def test_digest_changes_iff_file_content_changes(generate_function, fs, request):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    print(f"With data:\n{json.dumps(fs.sourcedata, indent=4)}")
    m1 = generate_function(fs.basepath)
    print("Merkle Digest Before:")
    utils.dump(m1, sys.stdout)
    print()
    file = random.choice([p for p in fs.basepath.rglob("**/*") if p.is_file()])
    with file.open(mode="w", encoding="utf-8") as fp:
        fp.write("Hello World")
    print(f"Modifying content of file: {file}")
    m2 = generate_function(fs.basepath)
    print("Merkle Digest After:")
    utils.dump(m2, sys.stdout)
    print()
    assert_merkle(m1, m2, modified_file=file)


@pytest.mark.parametrize("generate_function", generates)
@pytest.mark.parametrize(
    "fs",
    [
        {"dmerk_tests": {"file1": "Hello World 1", "file2": "Hello World 2"}},
    ],
    indirect=True,
)
def test_digest_same_if_file_or_dir_metadata_changes(generate_function, fs, request):
    """
    Metadata includes permissions, owner, group, atime, mtime, ctime
    """
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    print(f"With data:\n{json.dumps(fs.sourcedata, indent=4)}")
    m1 = generate_function(fs.basepath)
    print("Merkle Digest Before:")
    utils.dump(m1, sys.stdout)
    print()
    file = random.choice([p for p in fs.basepath.rglob("**/*") if p.is_file()])
    directory = random.choice([p for p in fs.basepath.rglob("**/*") if p.is_dir()])
    update_metadata(file)
    update_metadata(directory)
    print(f"Updating metadata of file: '{file}' and directory: '{directory}'")
    m2 = generate_function(fs.basepath)
    print("Merkle Digest After:")
    utils.dump(m2, sys.stdout)
    print()
    assert_merkle(m1, m2)


@pytest.mark.parametrize("generate_function", generates)
@pytest.mark.parametrize(
    "fs",
    [
        {"dmerk_tests": {"file1": "Hello World 1", "file2": "Hello World 2"}},
    ],
    indirect=True,
)
def test_digest_same_if_file_renamed(generate_function, fs, request):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    print(f"With data:\n{json.dumps(fs.sourcedata, indent=4)}")
    m1 = generate_function(fs.basepath)
    print("Merkle Digest Before:")
    utils.dump(m1, sys.stdout)
    print()
    file = random.choice([p for p in fs.basepath.rglob("**/*") if p.is_file()])
    file.rename(file.parent / "renamed_file")
    print(f"Renamed file: '{file}'")
    m2 = generate_function(fs.basepath)
    print("Merkle Digest After:")
    utils.dump(m2, sys.stdout)
    print()
    assert_merkle(m1, m2, renamed_file=(file, file.parent / "renamed_file"))
