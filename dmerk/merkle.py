import enum
import typing
import random
import string
import json
import pathlib
from pathlib import Path


class Merkle:
    __slots__ = ("path", "type", "size", "digest", "children")

    class Type(enum.Enum):
        FILE = "file"
        DIRECTORY = "directory"
        SYMLINK = "symlink"

        def __repr__(self):
            return str(self)

    def __init__(
        self,
        path: Path,
        type: Type,
        size: int,
        digest: str,
        # typing.Self only available from 3.11
        children: dict[Path, "Merkle"] | None = None,
    ) -> None:
        self.path = path
        self.type = type
        self.size = size
        self.digest = digest
        self.children = children

    def __eq__(self, other):
        if not isinstance(other, Merkle):
            return False
        else:
            return all(
                [
                    (getattr(self, slotname) == getattr(other, slotname))
                    if (hasattr(self, slotname) and hasattr(other, slotname))
                    else False
                    for slotname in Merkle.__slots__
                ]
            )

    def __hash__(self):
        return hash(tuple([getattr(self, slotname) for slotname in Merkle.__slots__]))

    def __repr__(self):
        kwargs = {
            slotname: getattr(self, slotname)
            for slotname in self.__slots__
            if hasattr(self, slotname)
        }
        argstring = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
        return f"{type(self).__name__}({argstring})"

    def __str__(self):
        return json.dumps(self, default=Merkle.json_encode, ensure_ascii=False)

    def traverse(self, subpath: Path) -> "Merkle":
        if not subpath.absolute():
            subpath = self.path / subpath
        if self.children is not None:
            for p, m in self.children.items():
                if subpath == p:
                    return m
                elif subpath.is_relative_to(p):
                    return m.traverse(subpath=subpath)
        raise ValueError(
            f"No sub-merkle found for path '{subpath}' in merkle rooted at {self.path}"
        )

    @staticmethod
    def _get_filename(path: Path) -> str:
        filename_path = Path(f"{path.name}.dmerk")
        while filename_path.exists():
            random_hex_string = "".join(random.choices(string.hexdigits.lower(), k=8))
            filename_path = Path(f"{path.name}_{random_hex_string}.dmerk")
        return filename_path.name

    def save(self, filename: str | None = None) -> None:
        if filename is None:
            filename = Merkle._get_filename(self.path)
        with open(filename, mode="w", encoding="utf-8") as file:
            json.dump(self, file, default=Merkle.json_encode, ensure_ascii=False)
        print(f"Saved merkle for path: '{self.path}' to file: '{filename}'")
        return filename

    @staticmethod
    def load(filename: str) -> "Merkle":
        with open(filename, mode="r", encoding="utf-8") as file:
            return json.load(file, object_hook=Merkle.json_decode)

    @staticmethod
    def json_encode(obj: typing.Any) -> dict[str, typing.Any]:
        if isinstance(obj, Merkle):
            output = {
                slotname: getattr(obj, slotname)
                for slotname in obj.__slots__
                if hasattr(obj, slotname)
            }
            output["__merkle__"] = True  # To make deserialization work :)
            # Need the below hack because of https://github.com/python/cpython/issues/63020
            output["path"] = repr(output["path"].absolute())
            if output["children"] is not None:
                output["children"] = {
                    repr(k.absolute()): v for k, v in output["children"].items()
                }
            return output
        elif isinstance(obj, Merkle.Type):
            return {"__merkle_type__": str(obj)}
        raise TypeError(f"Object of type {type(obj)} are not JSON serializable")

    @staticmethod
    def json_decode(obj: dict[str, typing.Any]) -> typing.Any:
        if "__merkle__" in obj:
            PosixPath = pathlib.PosixPath  # noqa: F841
            WindowsPath = pathlib.WindowsPath  # noqa: F841
            obj["path"] = eval(obj["path"])
            if obj["children"] is not None:
                globs = globals()
                locs = locals()
                obj["children"] = {
                    eval(k, globs, locs): v for k, v in obj["children"].items()
                }
            obj.pop("__merkle__")
            return Merkle(**obj)
        elif "__merkle_type__" in obj:
            Type = Merkle.Type  # noqa: F841
            return eval(obj["__merkle_type__"])
        else:
            return obj
