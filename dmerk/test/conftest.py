import collections
import os
import pathlib
import shutil
import typing

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line("markers", "profile: mark test as a profiling test")


def _fs(data: dict, base_path: pathlib.Path) -> None:
    for k, v in data.items():
        if not isinstance(k, typing.Union[str, bytes, os.PathLike]):
            raise TypeError(f"Bad type {type(k)}")
        if isinstance(v, dict):
            (base_path / k).mkdir()
            _fs(v, base_path / k)
        elif isinstance(v, str):
            with open(base_path / k, "w", encoding="utf-8") as file:
                file.write(v)
        else:
            raise TypeError(f"Bad type {type(v)}")


@pytest.fixture
def fs(request):
    """
    data should be a dictionary

    At the top-level, data should only contain a single key.
    In other words, this function is for creating a single test directory, not multiple test directories

    At any level in the dict, for a key-value pair k,v,
        if v is a dict, that means that k is a directory
        if v is a string, then k is a file containing the content v (encoded as utf-8)
    """
    data = request.param
    if len(data) > 1:
        raise ValueError("Too many items")
    base_path = pathlib.Path("TEST_DATA/NORMAL")
    if base_path.exists():
        shutil.rmtree(base_path)
        base_path.mkdir()
    else:
        base_path.mkdir()
    _fs(data, base_path)
    yield collections.namedtuple("FS", ["basepath", "sourcedata"])(base_path, data)
    shutil.rmtree(base_path)


def update_metadata(path, mode=None):
    if mode is None:
        # default permission for dir and file created by fs fixture is 775 and 664
        mode = 0o777
    path.chmod(mode=mode)
    # TODO: Can't change ownership without being root. Do I really want to run this test case as root???
    # shutil.chown(str(path), "root", "root")  # pathlib chown is in PR (https://github.com/python/cpython/issues/64978)
    path.touch()  # atime and ctime should have been modified by above commands, we just need to update mtime with touch


def assert_merkle(m1, m2, modified_file=None, renamed_file=None):
    keyset = m1.keys() | m2.keys()
    for k in keyset:
        try:
            v1 = m1[k]
            v2 = m2[k]
        except KeyError:
            if renamed_file:
                (old_file, new_file) = renamed_file
                if old_file.resolve() == k.resolve():
                    v1 = m1[k]
                    v2 = m2[new_file]
                elif new_file.resolve() == k.resolve():
                    v1 = m1[old_file]
                    v2 = m2[k]
            else:
                raise
        if modified_file and modified_file.resolve().is_relative_to(k.resolve()):
            assert v1["_digest"] != v2["_digest"]
        else:
            assert v1["_digest"] == v2["_digest"]
        assert v1["_type"] == v2["_type"]
        if v1["_type"] == v2["_type"] == "directory":
            assert_merkle(
                v1["_children"],
                v2["_children"],
                modified_file=modified_file,
                renamed_file=renamed_file,
            )
