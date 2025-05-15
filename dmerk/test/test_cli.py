import textwrap
import json
import logging
from pathlib import Path

import pytest

from .. import cli
from .. import generate
from .. import constants


@pytest.mark.parametrize("args", ("-h", "--help"))
def test_help(capsys, args):
    with pytest.raises(SystemExit):
        cli._main([args])
    captured = capsys.readouterr()
    assert "usage: dmerk [-h] [--no-save] {generate,compare,tui}" in captured.out
    assert (
        "Program to generate, compare and analyse directory merkle trees"
        in captured.out
    )


def test_subcommand_required(capsys):
    with pytest.raises(SystemExit):
        cli._main([])
    captured = capsys.readouterr()
    assert "usage: dmerk [-h] [--no-save] {generate,compare,tui}" in captured.err
    assert (
        "dmerk: error: the following arguments are required: {generate,compare,tui}"
        in captured.err
    )


@pytest.mark.parametrize("args", ("-h", "--help"))
def test_generate_help(capsys, args):
    with pytest.raises(SystemExit):
        cli._main(["generate", args])
    captured = capsys.readouterr()
    assert (
        "usage: dmerk generate [-h] [-p] [-f FILENAME] [--continue-on-error] path"
        in captured.out
    )
    assert "Generate a merkle tree for a given directory" in captured.out


def test_generate_path_required(capsys):
    with pytest.raises(SystemExit):
        cli._main(["generate"])
    captured = capsys.readouterr()
    assert (
        "usage: dmerk generate [-h] [-p] [-f FILENAME] [--continue-on-error] path"
        in captured.err
    )
    assert (
        "dmerk generate: error: the following arguments are required: path"
        in captured.err
    )


@pytest.mark.parametrize(
    "fs",
    [
        {"dmerk_tests": {"dir1": {"file1": "Hello World 1", "file2": "Hello World 2"}}},
    ],
    indirect=True,
)
def test_generate(capsys, fs):
    cli._main(["--no-save", "generate", str(fs.basepath.resolve())])
    captured = capsys.readouterr()
    assert captured.out.strip() == str(generate.generate(fs.basepath)).strip()


@pytest.mark.parametrize(
    "fs",
    [
        {"dmerk_tests": {"dir1": {"file1": "Hello World 1", "file2": "Hello World 2"}}},
    ],
    indirect=True,
)
def test_generate_save(caplog, fs):
    with caplog.at_level(logging.INFO):
        path = str(fs.basepath.resolve())
        saved_file = Path(constants.APP_STATE_PATH) / Path("NORMAL.dmerk")
        cli._main(["generate", path])
        assert f"Generating merkle for path: '{path}'" in caplog.text
        assert f"Saved merkle for path: '{path}' to file: '{saved_file}'" in caplog.text
        assert saved_file.exists()
        saved_file.unlink()


@pytest.mark.parametrize("args", ("-h", "--help"))
def test_compare_help(capsys, args):
    with pytest.raises(SystemExit):
        cli._main(["compare", args])
    captured = capsys.readouterr()
    assert (
        "dmerk compare [-h] -p1 PATH1 -p2 PATH2 [-sp1 SUBPATH1] [-sp2 SUBPATH2]"
        in captured.out
    )
    assert (
        "Compare two directory merkle trees and return the diffs and matches."
        in captured.out
    )
    assert (
        textwrap.dedent(
            """
            path1 and path2 are required, and they are the paths to the directories to compare,
            but they can also be paths to .dmerk files that were created using generate.
            Example: `dmerk -p1=/home/raghuram/Documents -p2=/media/raghuram/BACKUP_DRIVE/Documents`
            Example: `dmerk -p1=Documents_e6eaccb4.dmerk -p2=Documents_b2a7cef7.dmerk`
            """
        )
        in captured.out
    )


def test_compare_paths_required(capsys):
    with pytest.raises(SystemExit):
        cli._main(["compare"])
    captured = capsys.readouterr()
    assert (
        "dmerk compare [-h] -p1 PATH1 -p2 PATH2 [-sp1 SUBPATH1] [-sp2 SUBPATH2]"
        in captured.err
    )
    assert (
        "dmerk compare: error: the following arguments are required: -p1/--path1, -p2/--path2"
        in captured.err
    )


@pytest.mark.parametrize(
    "fs",
    [
        {
            "dmerk_tests": {
                "dir1": {"fileA": "Hello World A", "fileB": "Hello World B"},
                "dir2": {"fileA": "Hello World A", "fileC": "Hello World C"},
                "dir3": {"fileA": "Hello World A", "fileB": "Hello World B"},
            }
        },
    ],
    indirect=True,
)
@pytest.mark.parametrize(
    "path1,path2,output",
    [
        (
            "dmerk_tests/dir1",
            "dmerk_tests/dir2",
            {
                "matches": [
                    [
                        [
                            "/home/raghuram/Workspace/dmerk/TEST_DATA/NORMAL/dmerk_tests/dir1/fileA"
                        ],
                        [
                            "/home/raghuram/Workspace/dmerk/TEST_DATA/NORMAL/dmerk_tests/dir2/fileA"
                        ],
                    ]
                ],
                "unmatched_1": [
                    [
                        "/home/raghuram/Workspace/dmerk/TEST_DATA/NORMAL/dmerk_tests/dir1/fileB"
                    ]
                ],
                "unmatched_2": [
                    [
                        "/home/raghuram/Workspace/dmerk/TEST_DATA/NORMAL/dmerk_tests/dir2/fileC"
                    ]
                ],
            },
        ),
        (
            "dmerk_tests/dir1",
            "dmerk_tests/dir3",
            {
                "matches": [
                    [
                        [
                            "/home/raghuram/Workspace/dmerk/TEST_DATA/NORMAL/dmerk_tests/dir1"
                        ],
                        [
                            "/home/raghuram/Workspace/dmerk/TEST_DATA/NORMAL/dmerk_tests/dir3"
                        ],
                    ]
                ],
                "unmatched_1": [],
                "unmatched_2": [],
            },
        ),
    ],
)
def test_compare(capsys, fs, path1, path2, output):
    cli._main(
        [
            "--no-save",
            "compare",
            "-p1",
            str(fs.basepath / path1),
            "-p2",
            str(fs.basepath / path2),
        ]
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out) == output


@pytest.mark.asyncio
async def test_tui(monkeypatch):
    called = False

    def mock_run_tui():
        nonlocal called
        called = True

    monkeypatch.setattr(cli, "run_tui", mock_run_tui)
    assert called is False
    cli._main(["tui"])
    assert called is True


# Note:
#  Not adding tests that validates that generate saves output to json file.
#  This will be cumbersome to write, and doesn't add much value.
