import textwrap

import pytest

from .. import cli

@pytest.mark.parametrize("args", ("-h", "--help"))
def test_help(capsys, args):
    with pytest.raises(SystemExit):
        cli.main([args])
    captured = capsys.readouterr()
    assert "usage: dmerk [-h] {generate,compare,analyse}" in captured.out
    assert "Program to generate, compare and analyse directory merkle trees" in captured.out

def test_subcommand_required(capsys):
    with pytest.raises(SystemExit):
        cli.main([])
    captured = capsys.readouterr()
    assert "usage: dmerk [-h] {generate,compare,analyse}" in captured.err
    assert "dmerk: error: the following arguments are required: {generate,compare,analyse}" in captured.err

@pytest.mark.parametrize("args", ("-h", "--help"))
def test_generate_help(capsys, args):
    with pytest.raises(SystemExit):
        cli.main(["generate", args])
    captured = capsys.readouterr()
    assert "usage: dmerk generate [-h] [-n] [-p] [-f FILENAME] path" in captured.out
    assert "Generate a merkle tree for a given directory" in captured.out

def test_generate_path_required(capsys):
    with pytest.raises(SystemExit):
        cli.main(["generate"])
    captured = capsys.readouterr()
    assert "usage: dmerk generate [-h] [-n] [-p] [-f FILENAME] path" in captured.err
    assert "dmerk generate: error: the following arguments are required: path" in captured.err

@pytest.mark.parametrize("fs",
    [
        {"dmerk_tests":{"dir1":{"file1":"Hello World 1","file2":"Hello World 2"}}},
    ],
    indirect=True)
def test_generate(capsys, fs):
    cli.main(["generate", str(fs.basepath.resolve()), "--no-save"])
    captured = capsys.readouterr()
    assert textwrap.dedent('''
        {
            "/home/raghuram/Workspace/dmerk/TEST_DATA/NORMAL": {
                "_children": {
                    "dmerk_tests": {
                        "_children": {
                            "dir1": {
                                "_children": {
                                    "file1": {
                                        "_digest": "3fe10bf44e9a7deab63ea946c04fbcd8",
                                        "_type": "file"
                                    },
                                    "file2": {
                                        "_digest": "4c24aac86aa49adce486631bf365098f",
                                        "_type": "file"
                                    }
                                },
                                "_digest": "1ccaa0c417f6a789bbff45e836fcfa1b",
                                "_type": "directory"
                            }
                        },
                        "_digest": "392849b97d29bf246fdea845a8393b10",
                        "_type": "directory"
                    }
                },
                "_digest": "622e8ed459729cc72f6b63f7628ed390",
                "_type": "directory"
            }
        }
    ''').strip() in captured.out

@pytest.mark.parametrize("args", ("-h", "--help"))
def test_compare_help(capsys, args):
    with pytest.raises(SystemExit):
        cli.main(["compare", args])
    captured = capsys.readouterr()
    assert "usage: dmerk compare [-h] path1 path2" in captured.out
    assert textwrap.dedent("""
        Compare two directory merkle trees and return the diffs and matches.
        path1 and path2 are the paths to the directories,
        but they can also be paths to json files that were created using generate.
    """) in captured.out

def test_compare_paths_required(capsys):
    with pytest.raises(SystemExit):
        cli.main(["compare"])
    captured = capsys.readouterr()
    assert "usage: dmerk compare [-h] path1 path2" in captured.err
    assert "dmerk compare: error: the following arguments are required: path1, path2" in captured.err

@pytest.mark.parametrize("args", ("-h", "--help"))
def test_analyse_help(capsys, args):
    with pytest.raises(SystemExit):
        cli.main(["analyse", args])
    captured = capsys.readouterr()
    assert "usage: dmerk analyse [-h] path" in captured.out
    assert "Analyse a merkle tree to find copies/duplicates within" in captured.out

def test_analyse_path_required(capsys):
    with pytest.raises(SystemExit):
        cli.main(["analyse"])
    captured = capsys.readouterr()
    assert "usage: dmerk analyse [-h] path" in captured.err
    assert "dmerk analyse: error: the following arguments are required: path" in captured.err

# Note:
#  Not adding tests that validates that generate saves output to json file.
#  This will be cumbersome to write, and doesn't add much value.
