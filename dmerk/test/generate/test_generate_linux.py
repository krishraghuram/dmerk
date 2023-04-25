import contextlib
import json
import pathlib
import stat
import sys

import pytest

from ...generate import default_generate
from ... import utils
from ..conftest import assert_merkle

if sys.platform.startswith("linux"):
    generates = [default_generate]
else:
    generates = []


@pytest.mark.parametrize("generate_function", generates)
@pytest.mark.parametrize(
    "fs",
    [
        {"dmerk_tests": {"file": "Hello World", "symlink": "file"}},
    ],
    indirect=True,
)
def test_symlink(generate_function, fs, request):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    print(f"With data:\n{json.dumps(fs.sourcedata, indent=4)}")
    dmerk_tests = fs.basepath / "dmerk_tests"
    file = dmerk_tests / "file"
    symlink = dmerk_tests / "symlink"
    m1 = generate_function(fs.basepath, exclude=[])
    # need to manually modify _type of symlink
    m1[fs.basepath]["_children"][dmerk_tests]["_children"][symlink]["_type"] = "symlink"
    print("Merkle Digest Before:")
    utils.dump(m1, sys.stdout)
    print()
    symlink.unlink()
    symlink.symlink_to(file.name)
    print(f"Created symlink to file: {file}")
    m2 = generate_function(fs.basepath, exclude=[])
    print("Merkle Digest After:")
    utils.dump(m2, sys.stdout)
    print()
    assert_merkle(m1, m2)


@pytest.mark.parametrize("generate_function", generates)
@pytest.mark.parametrize(
    "path_and_error",
    [
        (pathlib.Path.cwd() / "TEST_DATA/SPECIAL/BLOCK_DEVICE", ValueError),
        (pathlib.Path.cwd() / "TEST_DATA/SPECIAL/CHAR_DEVICE", ValueError),
        (pathlib.Path.cwd() / "TEST_DATA/SPECIAL/NAMEDPIPE", ValueError),
        (pathlib.Path.cwd() / "TEST_DATA/SPECIAL/SOCKET", ValueError),
        (pathlib.Path.cwd() / "TEST_NONEXISTENT_DIRECTORY", NotADirectoryError),
    ],
)
def test_specialfiles(generate_function, path_and_error, request):
    """
    Run create_test_directories.sh before running tests

    TODO:
    Create the test directories within the test setup itself, and tear them down at the end
    Currently I've created create_test_directories.sh as a separate script because some commands inside it require sudo,
    and I don't want to run the entire suite of tests with root privileges.
    """
    (path, error) = path_and_error
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    print(f"With path '{path}' and error '{error}'")
    with pytest.raises(error):
        generate_function(path, exclude=[])


@pytest.mark.parametrize("generate_function", generates)
@pytest.mark.parametrize(
    "fs",
    [
        {"dmerk_tests": {"file": "Hello World"}},
    ],
    indirect=True,
)
@pytest.mark.parametrize(
    "mode,error,error_message",
    [
        (0o444, contextlib.nullcontext(None), None),
        (0o333, pytest.raises(PermissionError), "Permission denied"),
    ],
)
def test_file_permission(generate_function, fs, request, mode, error, error_message):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    print(f"With data:\n{json.dumps(fs.sourcedata, indent=4)}")
    file = fs.basepath / "dmerk_tests" / "file"

    original_mode = file.stat().st_mode

    file.chmod(mode=mode)
    print(
        f"Updated permissions of file '{file}' to '{oct(mode)}' ({stat.filemode(mode)[1:]})"
    )
    with error as e:
        m1 = generate_function(fs.basepath, exclude=[])
        print("Merkle Digest:")
        utils.dump(m1, sys.stdout)
        print()
    if e is not None:
        assert isinstance(e.value, error.expected_exception)
        assert error_message in [str(i) for i in e.value.args]
        print(f"Got expected exception: {repr(e.value)}")

    print("Resetting permissions so that fs fixture cleanup can occur properly...")
    file.chmod(mode=original_mode)


@pytest.mark.parametrize("generate_function", generates)
@pytest.mark.parametrize(
    "fs",
    [
        {"dmerk_tests": {"file": "Hello World"}},
    ],
    indirect=True,
)
@pytest.mark.parametrize(
    "mode,error",
    [
        (0o555, contextlib.nullcontext(None)),
        (0o666, pytest.raises(PermissionError)),
        (0o333, pytest.raises(PermissionError)),
    ],
)
def test_directory_permission(generate_function, fs, request, mode, error):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    print(f"With data: {json.dumps(fs.sourcedata)}")
    directory = fs.basepath / "dmerk_tests"

    original_mode = directory.stat().st_mode

    directory.chmod(mode=mode)
    print(
        f"Updated permissions of directory '{directory}' to '{oct(mode)}' ({stat.filemode(mode)[1:]})"
    )
    with error as e:
        m1 = generate_function(fs.basepath, exclude=[])
        print("Merkle Digest:")
        utils.dump(m1, sys.stdout)
        print()
    if e is not None:
        assert isinstance(e.value, error.expected_exception)
        print(f"Got expected exception: {repr(e.value)}")

    print("Resetting permissions so that fs fixture cleanup can occur properly...")
    directory.chmod(mode=original_mode)
