import json
import random
from pathlib import Path

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
            Path("file"): Merkle(Path("file"), Merkle.Type.FILE, 100, "sha_digest_1_a")
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


@pytest.mark.parametrize("kwargs", MERKLE_KWARGS)
def test_merkle_eq(kwargs):
    m = Merkle(**kwargs)
    assert m == Merkle(**kwargs)
    assert m != None
    assert m == Merkle(**{**kwargs, "path": Path("/home/raghuram/foo")})
    assert m != Merkle(**{**kwargs, "type": Merkle.Type.FILE})
    assert m != Merkle(**{**kwargs, "size": 2000})
    assert m != Merkle(**{**kwargs, "digest": "sha_digest_2"})
    assert m != Merkle(**{**kwargs, "children": {}})


@pytest.mark.parametrize("kwargs", MERKLE_KWARGS[1:2])
def test_merkle_repr(kwargs):
    m = Merkle(**kwargs)
    repr_m = "Merkle(path=PosixPath('/home/raghuram'), type=Type.DIRECTORY, size=1000, digest='sha_digest_1', children={PosixPath('file'): Merkle(path=PosixPath('file'), type=Type.FILE, size=100, digest='sha_digest_1_a')})"
    assert repr(m) == repr_m


@pytest.mark.parametrize("kwargs", MERKLE_KWARGS[1:2])
def test_merkle_str(kwargs):
    m = Merkle(**kwargs)
    str_m = '{"path": "PosixPath(\'/home/raghuram\')", "type": {"__merkle_type__": "Type.DIRECTORY"}, "size": 1000, "digest": "sha_digest_1", "children": {"PosixPath(\'/home/raghuram/Workspace/dmerk/file\')": {"path": "PosixPath(\'/home/raghuram/Workspace/dmerk/file\')", "type": {"__merkle_type__": "Type.FILE"}, "size": 100, "digest": "sha_digest_1_a", "__merkle__": true}}, "__merkle__": true}'
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
    filename_1 = Merkle._get_filename(path)
    assert filename_1 == Path.cwd() / Path(f"{path.name}.dmerk")
    monkeypatch.setattr(Path, "exists", lambda p: p.name == filename_1.name)
    monkeypatch.setattr(random, "choices", lambda *args, **kwargs: ["0"] * 8)
    filename_2 = Merkle._get_filename(path)
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
    Path(filename).unlink()
    assert m == m2


def test_merkle_json_encode_type_error():
    class Foo:
        pass

    with pytest.raises(TypeError):
        json.dumps(Foo(), default=Merkle.json_encode, ensure_ascii=False)
