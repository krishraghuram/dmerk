import textwrap
from pathlib import Path

import pytest

from .. import cli
from .. import generate


@pytest.mark.parametrize("args", ("-h", "--help"))
def test_help(capsys, args):
    with pytest.raises(SystemExit):
        cli._main([args])
    captured = capsys.readouterr()
    assert "usage: dmerk [-h] [--no-save] {generate,compare}" in captured.out
    assert (
        "Program to generate, compare and analyse directory merkle trees"
        in captured.out
    )


def test_subcommand_required(capsys):
    with pytest.raises(SystemExit):
        cli._main([])
    captured = capsys.readouterr()
    assert "usage: dmerk [-h] [--no-save] {generate,compare}" in captured.err
    assert (
        "dmerk: error: the following arguments are required: {generate,compare}"
        in captured.err
    )


@pytest.mark.parametrize("args", ("-h", "--help"))
def test_generate_help(capsys, args):
    with pytest.raises(SystemExit):
        cli._main(["generate", args])
    captured = capsys.readouterr()
    assert "usage: dmerk generate [-h] [-p] [-f FILENAME] path" in captured.out
    assert "Generate a merkle tree for a given directory" in captured.out


def test_generate_path_required(capsys):
    with pytest.raises(SystemExit):
        cli._main(["generate"])
    captured = capsys.readouterr()
    assert "usage: dmerk generate [-h] [-p] [-f FILENAME] path" in captured.err
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
def test_generate_save(capsys, fs):
    cli._main(["generate", str(fs.basepath.resolve())])
    captured = capsys.readouterr()
    assert (
        captured.out.strip()
        == "Saved merkle for path: '/home/raghuram/Workspace/dmerk/TEST_DATA/NORMAL' to file: 'NORMAL.dmerk'"
    )
    assert Path("NORMAL.dmerk").exists()
    Path("NORMAL.dmerk").unlink()


# @pytest.mark.parametrize("args", ("-h", "--help"))
# def test_compare_help(capsys, args):
#     with pytest.raises(SystemExit):
#         cli._main(["compare", args])
#     captured = capsys.readouterr()
#     assert "usage: dmerk compare [-h] path1 path2" in captured.out
#     assert (
#         textwrap.dedent(
#             """
#         Compare two directory merkle trees and return the diffs and matches.
#         path1 and path2 are the paths to the directories,
#         but they can also be paths to json files that were created using generate.
#     """
#         )
#         in captured.out
#     )


# def test_compare_paths_required(capsys):
#     with pytest.raises(SystemExit):
#         cli._main(["compare"])
#     captured = capsys.readouterr()
#     assert "usage: dmerk compare [-h] path1 path2" in captured.err
#     assert (
#         "dmerk compare: error: the following arguments are required: path1, path2"
#         in captured.err
#     )


# @pytest.mark.parametrize("args", ("-h", "--help"))
# def test_analyse_help(capsys, args):
#     with pytest.raises(SystemExit):
#         cli._main(["analyse", args])
#     captured = capsys.readouterr()
#     assert "usage: dmerk analyse [-h] path" in captured.out
#     assert "Analyse a merkle tree to find copies/duplicates within" in captured.out


# def test_analyse_path_required(capsys):
#     with pytest.raises(SystemExit):
#         cli._main(["analyse"])
#     captured = capsys.readouterr()
#     assert "usage: dmerk analyse [-h] path" in captured.err
#     assert (
#         "dmerk analyse: error: the following arguments are required: path"
#         in captured.err
#     )


# Note:
#  Not adding tests that validates that generate saves output to json file.
#  This will be cumbersome to write, and doesn't add much value.
