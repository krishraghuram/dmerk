import json
import logging
import random
from pathlib import Path, PurePosixPath

import pytest

from ..merkle import Merkle

MERKLE_KWARGS = [
    {
        "path": Path("/home/raghuram/"),
        "type": Merkle.Type.DIRECTORY,
        "size": 1000,
        "digest": "sha_digest_1",
        "children": None,
    },
    {
        "path": Path("/home/raghuram/"),
        "type": Merkle.Type.DIRECTORY,
        "size": 1000,
        "digest": "sha_digest_1",
        "children": {
            PurePosixPath("/home/raghuram/file"): Merkle(
                PurePosixPath("/home/raghuram/file"),
                Merkle.Type.FILE,
                100,
                "sha_digest_1_a",
            )
        },
    },
]


@pytest.mark.parametrize("kwargs", MERKLE_KWARGS)
def test_merkle_init(kwargs):
    m = Merkle(*list(kwargs.values()))
    m2 = Merkle(**kwargs)
    assert m.path == m2.path == kwargs["path"]
    assert m.type == m2.type == kwargs["type"]
    assert m.size == m2.size == kwargs["size"]
    assert m.digest == m2.digest == kwargs["digest"]
    if kwargs["children"]:
        assert m.children == m2.children == kwargs["children"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "path": PurePosixPath("raghuram"),
            "type": Merkle.Type.DIRECTORY,
            "size": 1000,
            "digest": "sha_digest_1",
            "children": None,
        }
    ],
)
def test_merkle_init_non_absolute_purepath_error(kwargs):
    with pytest.raises(ValueError) as excinfo:
        Merkle(**kwargs)
    assert f"Cannot handle non-absolute PurePath {kwargs['path']} !!!" in str(
        excinfo.value
    )


@pytest.mark.parametrize("kwargs", MERKLE_KWARGS)
def test_merkle_eq(kwargs):
    m = Merkle(**kwargs)
    assert m == Merkle(**kwargs)
    assert m != None
    assert m == Merkle(**{**kwargs, "path": Path("/home/raghuram/foo")})
    assert m != Merkle(**{**kwargs, "type": Merkle.Type.FILE})
    assert m != Merkle(**{**kwargs, "size": 2000})
    assert m != Merkle(**{**kwargs, "digest": "sha_digest_2"})


@pytest.mark.parametrize("kwargs", MERKLE_KWARGS[1:2])
def test_merkle_repr(kwargs):
    m = Merkle(**kwargs)
    repr_m = "Merkle(path=PurePosixPath('/home/raghuram'), type=Type.DIRECTORY, size=1000, digest='sha_digest_1', children={PurePosixPath('/home/raghuram/file'): Merkle(path=PurePosixPath('/home/raghuram/file'), type=Type.FILE, size=100, digest='sha_digest_1_a', children={})})"
    assert repr(m) == repr_m


@pytest.mark.parametrize("kwargs", MERKLE_KWARGS[1:2])
def test_merkle_str(kwargs):
    m = Merkle(**kwargs)
    str_m = '{"path": "PurePosixPath(\'/home/raghuram\')", "type": {"__merkle_type__": "Type.DIRECTORY"}, "size": 1000, "digest": "sha_digest_1", "children": {"PurePosixPath(\'/home/raghuram/file\')": {"path": "PurePosixPath(\'/home/raghuram/file\')", "type": {"__merkle_type__": "Type.FILE"}, "size": 100, "digest": "sha_digest_1_a", "children": {}, "__merkle__": true}}, "__merkle__": true}'
    assert str(m) == str_m


@pytest.mark.parametrize(
    "merkle",
    [
        Merkle(
            Path("/home/raghuram/Documents"),
            Merkle.Type.DIRECTORY,
            1000,
            "digest_Documents",
            {
                Path("/home/raghuram/Documents/A"): Merkle(
                    Path("/home/raghuram/Documents/A"),
                    Merkle.Type.DIRECTORY,
                    200,
                    "digest_Documents_A",
                    {
                        Path("/home/raghuram/Documents/A/1"): Merkle(
                            Path("/home/raghuram/Documents/A/1"),
                            Merkle.Type.FILE,
                            100,
                            "digest_Documents_A_1",
                        )
                    },
                ),
                Path("/home/raghuram/Documents/B"): Merkle(
                    Path("/home/raghuram/Documents/B"),
                    Merkle.Type.DIRECTORY,
                    200,
                    "digest_Documents_B",
                    {
                        Path("/home/raghuram/Documents/B/2"): Merkle(
                            Path("/home/raghuram/Documents/B/2"),
                            Merkle.Type.FILE,
                            100,
                            "digest_Documents_B_2",
                        )
                    },
                ),
                Path("/home/raghuram/Documents/3"): Merkle(
                    Path("/home/raghuram/Documents/3"),
                    Merkle.Type.FILE,
                    100,
                    "digest_Documents_3",
                ),
            },
        )
    ],
)
@pytest.mark.parametrize(
    "subpath,return_value,exception",
    [
        (
            Path("/home/raghuram/Documents/A"),
            Merkle(
                Path("/home/raghuram/Documents/A"),
                Merkle.Type.DIRECTORY,
                200,
                "digest_Documents_A",
                {
                    Path("/home/raghuram/Documents/A/1"): Merkle(
                        Path("/home/raghuram/Documents/A/1"),
                        Merkle.Type.FILE,
                        100,
                        "digest_Documents_A_1",
                    )
                },
            ),
            None,
        ),
        (
            Path("B/2/"),
            Merkle(
                Path("/home/raghuram/Documents/B/2"),
                Merkle.Type.FILE,
                100,
                "digest_Documents_B_2",
            ),
            None,
        ),
        (
            Path("."),
            Merkle(
                Path("/home/raghuram/Documents"),
                Merkle.Type.DIRECTORY,
                1000,
                "digest_Documents",
                {
                    Path("/home/raghuram/Documents/A"): Merkle(
                        Path("/home/raghuram/Documents/A"),
                        Merkle.Type.DIRECTORY,
                        200,
                        "digest_Documents_A",
                        {
                            Path("/home/raghuram/Documents/A/1"): Merkle(
                                Path("/home/raghuram/Documents/A/1"),
                                Merkle.Type.FILE,
                                100,
                                "digest_Documents_A_1",
                            )
                        },
                    ),
                    Path("/home/raghuram/Documents/B"): Merkle(
                        Path("/home/raghuram/Documents/B"),
                        Merkle.Type.DIRECTORY,
                        200,
                        "digest_Documents_B",
                        {
                            Path("/home/raghuram/Documents/B/2"): Merkle(
                                Path("/home/raghuram/Documents/B/2"),
                                Merkle.Type.FILE,
                                100,
                                "digest_Documents_B_2",
                            )
                        },
                    ),
                    Path("/home/raghuram/Documents/3"): Merkle(
                        Path("/home/raghuram/Documents/3"),
                        Merkle.Type.FILE,
                        100,
                        "digest_Documents_3",
                    ),
                },
            ),
            None,
        ),
        (Path("/home/raghuram/Documents/4"), None, ValueError),
        (Path("5"), None, ValueError),
    ],
)
def test_merkle_traverse(merkle: Merkle, subpath, return_value, exception):
    if return_value is not None:
        assert return_value == merkle.traverse(subpath)
    elif exception is not None:
        with pytest.raises(exception):
            merkle.traverse(subpath)


def test_merkle_get_filename(monkeypatch):
    path = Path("/home/raghuram/Documents")
    filename_1 = Merkle._get_filename(path.name)
    assert filename_1 == Path.cwd() / Path(f"{path.name}.dmerk")
    monkeypatch.setattr(Path, "exists", lambda p: p.name == filename_1.name)
    monkeypatch.setattr(random, "choices", lambda *args, **kwargs: ["0"] * 8)
    filename_2 = Merkle._get_filename(path.name)
    assert filename_2 == Path.cwd() / Path(f"{path.name}_00000000.dmerk")


def test_merkle_save_load():
    # Not using monkeypatch here because pytest doesn't recommend
    # monkeypatching low-level stuff like `open`, since it could break pytest itself.
    # Ref: https://docs.pytest.org/en/latest/how-to/monkeypatch.html
    m = Merkle(
        Path("/home/raghuram/Documents"),
        Merkle.Type.DIRECTORY,
        1000,
        "digest_Documents",
        {
            Path("/home/raghuram/Documents/A"): Merkle(
                Path("/home/raghuram/Documents/A"),
                Merkle.Type.FILE,
                800,
                "digest_Documents_A",
            )
        },
    )
    filename = m.save()
    m2 = Merkle.load(filename)
    assert m2._children_data is not None
    assert m2._children is None
    assert m2.children == m.children  # trigger lazy-loading
    assert m2._children_data is None
    assert m2._children is not None
    Path(filename).unlink()
    assert m == m2


def test_merkle_json_encode_type_error():
    class Foo:
        pass

    with pytest.raises(TypeError):
        json.dumps(Foo(), default=Merkle.json_encode, ensure_ascii=False)


@pytest.mark.parametrize(
    "merkle_json,error_message",
    [
        (
            '{"path":"PurePosixPath(\'/home/raghuram/TEST\')","type":{"__merkle_type__":"Type.DIRECTORY"},"size":0,"digest":"d41d8cd98f00b204e9800998ecf8427e"}',
            "Not a valid Merkle dictionary",
        ),
        (
            '{"path":"PurePosixPath(\'/home/raghuram/TEST\')","type":"INVALID","size":0,"digest":"d41d8cd98f00b204e9800998ecf8427e","__merkle__":true}',
            "Not a valid Merkle.Type dictionary",
        ),
        (
            '{"path":"PurePosixPath(\'/home/raghuram/TEST\')","type":{},"size":0,"digest":"d41d8cd98f00b204e9800998ecf8427e","__merkle__":true}',
            "Not a valid Merkle.Type dictionary",
        ),
        (
            '{"path":"PurePosixPath(\'/home/raghuram/TEST\')","type":{"__merkle_type__":"Type.INVALID"},"size":0,"digest":"d41d8cd98f00b204e9800998ecf8427e","__merkle__":true}',
            "Not a valid Merkle.Type dictionary",
        ),
    ],
)
def test_load_invalid_merkle(tmp_path, caplog, merkle_json, error_message):
    caplog.set_level(logging.INFO)
    file = tmp_path / "invalid.dmerk"
    file.write_text(merkle_json)
    with pytest.raises(ValueError) as e:
        Merkle.load(file)
    assert str(e.value) == error_message
    assert error_message in caplog.text
