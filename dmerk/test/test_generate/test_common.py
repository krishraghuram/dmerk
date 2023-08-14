import random
from pathlib import PosixPath


import pytest


from ..conftest import update_metadata, assert_merkle
from ...generate import default_generate
from ...merkle import Merkle


Type = Merkle.Type


generates = [default_generate]


@pytest.mark.parametrize("generate_function", generates)
@pytest.mark.parametrize(
    "fs,merkle",
    [
        # Test basic case
        (
            {
                "dmerk_tests": {
                    "dir1": {"file1": "Hello World 1", "file2": "Hello World 2"}
                }
            },
            Merkle(
                path=PosixPath("TEST_DATA/NORMAL"),
                type=Type.DIRECTORY,
                size=12314,
                digest="622e8ed459729cc72f6b63f7628ed390",
                children={
                    PosixPath("TEST_DATA/NORMAL/dmerk_tests"): Merkle(
                        path=PosixPath("TEST_DATA/NORMAL/dmerk_tests"),
                        type=Type.DIRECTORY,
                        size=8218,
                        digest="392849b97d29bf246fdea845a8393b10",
                        children={
                            PosixPath("TEST_DATA/NORMAL/dmerk_tests/dir1"): Merkle(
                                path=PosixPath("TEST_DATA/NORMAL/dmerk_tests/dir1"),
                                type=Type.DIRECTORY,
                                size=4122,
                                digest="1ccaa0c417f6a789bbff45e836fcfa1b",
                                children={
                                    PosixPath(
                                        "TEST_DATA/NORMAL/dmerk_tests/dir1/file2"
                                    ): Merkle(
                                        path=PosixPath(
                                            "TEST_DATA/NORMAL/dmerk_tests/dir1/file2"
                                        ),
                                        type=Type.FILE,
                                        size=13,
                                        digest="4c24aac86aa49adce486631bf365098f",
                                    ),
                                    PosixPath(
                                        "TEST_DATA/NORMAL/dmerk_tests/dir1/file1"
                                    ): Merkle(
                                        path=PosixPath(
                                            "TEST_DATA/NORMAL/dmerk_tests/dir1/file1"
                                        ),
                                        type=Type.FILE,
                                        size=13,
                                        digest="3fe10bf44e9a7deab63ea946c04fbcd8",
                                    ),
                                },
                            )
                        },
                    )
                },
            ),
        ),
        # Test empty dir
        (
            {"dmerk_tests": {"dir1": {}}},
            Merkle(
                path=PosixPath("TEST_DATA/NORMAL"),
                type=Type.DIRECTORY,
                size=12288,
                digest="acf7ef943fdeb3cbfed8dd0d8f584731",
                children={
                    PosixPath("TEST_DATA/NORMAL/dmerk_tests"): Merkle(
                        path=PosixPath("TEST_DATA/NORMAL/dmerk_tests"),
                        type=Type.DIRECTORY,
                        size=8192,
                        digest="74be16979710d4c4e7c6647856088456",
                        children={
                            PosixPath("TEST_DATA/NORMAL/dmerk_tests/dir1"): Merkle(
                                path=PosixPath("TEST_DATA/NORMAL/dmerk_tests/dir1"),
                                type=Type.DIRECTORY,
                                size=4096,
                                digest="d41d8cd98f00b204e9800998ecf8427e",
                                children={},
                            )
                        },
                    )
                },
            ),
        ),
        # Test hidden files
        (
            {
                "dmerk_tests": {
                    ".dir1": {".file1": "Hello World 1", ".file2": "Hello World 2"}
                }
            },
            Merkle(
                path=PosixPath("TEST_DATA/NORMAL"),
                type=Type.DIRECTORY,
                size=12314,
                digest="622e8ed459729cc72f6b63f7628ed390",
                children={
                    PosixPath("TEST_DATA/NORMAL/dmerk_tests"): Merkle(
                        path=PosixPath("TEST_DATA/NORMAL/dmerk_tests"),
                        type=Type.DIRECTORY,
                        size=8218,
                        digest="392849b97d29bf246fdea845a8393b10",
                        children={
                            PosixPath("TEST_DATA/NORMAL/dmerk_tests/.dir1"): Merkle(
                                path=PosixPath("TEST_DATA/NORMAL/dmerk_tests/.dir1"),
                                type=Type.DIRECTORY,
                                size=4122,
                                digest="1ccaa0c417f6a789bbff45e836fcfa1b",
                                children={
                                    PosixPath(
                                        "TEST_DATA/NORMAL/dmerk_tests/.dir1/.file1"
                                    ): Merkle(
                                        path=PosixPath(
                                            "TEST_DATA/NORMAL/dmerk_tests/.dir1/.file1"
                                        ),
                                        type=Type.FILE,
                                        size=13,
                                        digest="3fe10bf44e9a7deab63ea946c04fbcd8",
                                    ),
                                    PosixPath(
                                        "TEST_DATA/NORMAL/dmerk_tests/.dir1/.file2"
                                    ): Merkle(
                                        path=PosixPath(
                                            "TEST_DATA/NORMAL/dmerk_tests/.dir1/.file2"
                                        ),
                                        type=Type.FILE,
                                        size=13,
                                        digest="4c24aac86aa49adce486631bf365098f",
                                    ),
                                },
                            )
                        },
                    )
                },
            ),
        ),
        # TODO: '\t' breaks tests in windows, need to find a way to fix this test-case
        # Test whitespace in filenames
        (
            {
                "dmerk_tests": {
                    "Dir 1": {
                        "File 1": "Hello World 1",
                        "'\tF i l e 2\t'": "Hello World 2",
                    }
                }
            },
            Merkle(
                path=PosixPath("TEST_DATA/NORMAL"),
                type=Type.DIRECTORY,
                size=12314,
                digest="622e8ed459729cc72f6b63f7628ed390",
                children={
                    PosixPath("TEST_DATA/NORMAL/dmerk_tests"): Merkle(
                        path=PosixPath("TEST_DATA/NORMAL/dmerk_tests"),
                        type=Type.DIRECTORY,
                        size=8218,
                        digest="392849b97d29bf246fdea845a8393b10",
                        children={
                            PosixPath("TEST_DATA/NORMAL/dmerk_tests/Dir 1"): Merkle(
                                path=PosixPath("TEST_DATA/NORMAL/dmerk_tests/Dir 1"),
                                type=Type.DIRECTORY,
                                size=4122,
                                digest="1ccaa0c417f6a789bbff45e836fcfa1b",
                                children={
                                    PosixPath(
                                        "TEST_DATA/NORMAL/dmerk_tests/Dir 1/'\tF i l e 2\t'"
                                    ): Merkle(
                                        path=PosixPath(
                                            "TEST_DATA/NORMAL/dmerk_tests/Dir 1/'\tF i l e 2\t'"
                                        ),
                                        type=Type.FILE,
                                        size=13,
                                        digest="4c24aac86aa49adce486631bf365098f",
                                    ),
                                    PosixPath(
                                        "TEST_DATA/NORMAL/dmerk_tests/Dir 1/File 1"
                                    ): Merkle(
                                        path=PosixPath(
                                            "TEST_DATA/NORMAL/dmerk_tests/Dir 1/File 1"
                                        ),
                                        type=Type.FILE,
                                        size=13,
                                        digest="3fe10bf44e9a7deab63ea946c04fbcd8",
                                    ),
                                },
                            )
                        },
                    )
                },
            ),
        ),
        # Test path names with unicode chars outside basic latin block
        (
            {"dmerk_tests": {"📁1": {"ファイル一": "こんにちは世界 一", "ファイル二": "こんにちは世界 二"}}},
            Merkle(
                path=PosixPath("TEST_DATA/NORMAL"),
                type=Type.DIRECTORY,
                size=12338,
                digest="ea7ce4b431c1555d2ff6b12825140546",
                children={
                    PosixPath("TEST_DATA/NORMAL/dmerk_tests"): Merkle(
                        path=PosixPath("TEST_DATA/NORMAL/dmerk_tests"),
                        type=Type.DIRECTORY,
                        size=8242,
                        digest="fb240654b9765dd3c960d174218a509e",
                        children={
                            PosixPath("TEST_DATA/NORMAL/dmerk_tests/📁1"): Merkle(
                                path=PosixPath("TEST_DATA/NORMAL/dmerk_tests/📁1"),
                                type=Type.DIRECTORY,
                                size=4146,
                                digest="7655839b2c033d4ee32cb61042ba795a",
                                children={
                                    PosixPath(
                                        "TEST_DATA/NORMAL/dmerk_tests/📁1/ファイル二"
                                    ): Merkle(
                                        path=PosixPath(
                                            "TEST_DATA/NORMAL/dmerk_tests/📁1/ファイル二"
                                        ),
                                        type=Type.FILE,
                                        size=25,
                                        digest="28141e877d44b6ddd5ae07f1a7ac11ef",
                                    ),
                                    PosixPath(
                                        "TEST_DATA/NORMAL/dmerk_tests/📁1/ファイル一"
                                    ): Merkle(
                                        path=PosixPath(
                                            "TEST_DATA/NORMAL/dmerk_tests/📁1/ファイル一"
                                        ),
                                        type=Type.FILE,
                                        size=25,
                                        digest="c5ebd17eea81b9db92864eeb9e60d71c",
                                    ),
                                },
                            )
                        },
                    )
                },
            ),
        ),
    ],
    indirect=["fs"],
)
def test_digest_correct(generate_function, fs, merkle, request):
    print(f"\n\n\n\n\nStarting Test: {request.node.name}")
    print(f"With {fs=}")
    m1 = generate_function(fs.basepath)
    print("Merkle Digest:")
    print(repr(m1))
    print("Expected Merkle Digest:")
    m2 = merkle
    print(m2)
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
    print(f"With {fs=}")
    m1 = generate_function(fs.basepath)
    print("Merkle Digest Before:")
    print(m1)
    file = random.choice([p for p in fs.basepath.rglob("**/*") if p.is_file()])
    with file.open(mode="w", encoding="utf-8") as fp:
        fp.write("Hello World")
    print(f"Modifying content of file: {file}")
    m2 = generate_function(fs.basepath)
    print("Merkle Digest After:")
    print(m2)
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
    print(f"With {fs=}")
    m1 = generate_function(fs.basepath)
    print("Merkle Digest Before:")
    print(m1)
    file = random.choice([p for p in fs.basepath.rglob("**/*") if p.is_file()])
    directory = random.choice([p for p in fs.basepath.rglob("**/*") if p.is_dir()])
    update_metadata(file)
    update_metadata(directory)
    print(f"Updating metadata of file: '{file}' and directory: '{directory}'")
    m2 = generate_function(fs.basepath)
    print("Merkle Digest After:")
    print(m2)
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
    print(f"With {fs=}")
    m1 = generate_function(fs.basepath)
    print("Merkle Digest Before:")
    print(m1)
    file = random.choice([p for p in fs.basepath.rglob("**/*") if p.is_file()])
    file.rename(file.parent / "renamed_file")
    print(f"Renamed file: '{file}'")
    m2 = generate_function(fs.basepath)
    print("Merkle Digest After:")
    print(m2)
    assert_merkle(m1, m2, renamed_file=(file, file.parent / "renamed_file"))
