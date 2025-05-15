import collections
import os
from pathlib import Path
import shutil
import typing

import pytest

from ..merkle import Merkle


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line("markers", "profile: mark test as a profiling test")
    config.addinivalue_line("markers", "perf: mark test as a perf test")


def _fs(data: dict, base_path: Path) -> None:
    for k, v in data.items():
        # Python 3.9 Compat
        # https://bugs.python.org/issue44529
        # https://stackoverflow.com/a/64643971/5530864
        if not isinstance(k, typing.get_args(typing.Union[str, bytes, os.PathLike])):
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
    base_path = Path("TEST_DATA/NORMAL")
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


def assert_merkle(
    m1: Merkle,
    m2: Merkle,
    modified_file: Path | None = None,
    renamed_file: tuple[Path, Path] | None = None,
):
    # TODO: ("path", "type", "size", "digest", "children")
    if not modified_file and not renamed_file:
        assert m1 == m2
    elif modified_file is not None:
        assert m1.path == m2.path
        assert m1.type == m2.type
        assert m1.size != m2.size
        assert m1.digest != m2.digest
        assert getattr(m1, "children", {}).keys() == getattr(m2, "children", {}).keys()
        for path in getattr(m1, "children", {}).keys():
            if modified_file.is_relative_to(path):
                assert_merkle(
                    m1.children[path], m2.children[path], modified_file=modified_file
                )
            else:
                assert_merkle(m1.children[path], m2.children[path])
    elif renamed_file is not None:
        (old_file, new_file) = renamed_file
        assert m1.path == m2.path
        assert m1.type == m2.type
        assert m1.size == m2.size
        assert m1.digest == m2.digest
        for path in (
            getattr(m1, "children", {}).keys() | getattr(m2, "children", {}).keys()
        ):
            if path in (old_file, new_file):
                assert_merkle(m1.children[old_file], m2.children[new_file])
            else:
                assert_merkle(
                    m1.children[path], m2.children[path], renamed_file=renamed_file
                )
