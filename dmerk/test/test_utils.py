from pathlib import Path

import pytest

import dmerk.generate
from dmerk.merkle import Merkle
from dmerk.utils import colorhash, fuzzy_match, load_or_generate


def test_load_or_generate_load(monkeypatch, tmp_path):
    mock_merkle = Merkle(Path(), 0, Merkle.Type.DIRECTORY, "")
    monkeypatch.setattr(Merkle, "load", lambda p: mock_merkle)
    path = tmp_path / "test.dmerk"
    path.touch()
    result = load_or_generate(path, no_save=True)
    assert result == mock_merkle


@pytest.mark.parametrize("no_save", [False, True])
def test_load_or_generate_generate_dir(monkeypatch, tmp_path, no_save):
    saved = False

    def save(m: Merkle):
        nonlocal saved
        saved = True

    monkeypatch.setattr(Merkle, "save", save)
    mock_merkle = Merkle(Path(), 0, Merkle.Type.DIRECTORY, "")
    monkeypatch.setattr(dmerk.generate, "generate", lambda p: mock_merkle)
    path = tmp_path / "test"
    path.mkdir()

    result = load_or_generate(path, no_save=no_save)
    assert result == mock_merkle
    assert no_save != saved


def test_load_or_generate_generate_file(tmp_path):
    path = tmp_path / "test"
    path.touch()
    with pytest.raises(NotADirectoryError):
        load_or_generate(path, no_save=True)


@pytest.mark.parametrize(
    "hash_hex_string,expected_return_value",
    [
        ("d41d8cd98f00b204e9800998ecf8427e", "rgb(240,59,246)"),
    ],
)
def test_colorhash(hash_hex_string, expected_return_value):
    result = colorhash(hash_hex_string)
    rgb_values = result[4:-1].split(",")
    assert len(rgb_values) == 3
    for val in rgb_values:
        assert 0 <= int(val) <= 255
    if expected_return_value is not None:
        assert result == expected_return_value


@pytest.mark.parametrize(
    "text,query,expected",
    [
        ("hello", "hello", True),
        ("Hello", "hello", True),
        ("HELLO", "hello", True),
        ("hello", "HELLO", True),
        ("hello world", "world", True),
        ("hello world", "hello", True),
        ("hello world", "lo wo", True),
        ("hello", "xyz", False),
        ("hello world", "foo", False),
        ("hello", "", True),
        ("anything", "", True),
        ("hello", None, True),
        ("anything", None, True),
        ("", "", True),
        ("", "query", False),
        ("", None, True),
    ],
)
def test_fuzzy_match(text, query, expected):
    assert fuzzy_match(text, query) == expected
