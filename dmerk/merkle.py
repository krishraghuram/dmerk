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
        if children is not None:
            self.children = children

    def __eq__(self, other):
        """
        Return True if self is equal to other, else False

        Note that two Merkles are equal even if their 'path' attribute is different
        This is because we only care about the data in the filesystem being same,
        and not the path at which it is present
        """
        if not isinstance(other, Merkle):
            return False
        else:
            return all(
                [
                    (getattr(self, slotname, None) == getattr(other, slotname, None))
                    for slotname in set(Merkle.__slots__) - {"path"}
                ]
            )

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

    def _traverse(self, subpath: Path) -> "Merkle":
        if subpath == self.path:
            return self
        elif hasattr(self, "children"):
            for p, m in self.children.items():
                if subpath == p:
                    return m
                elif subpath.is_relative_to(p):
                    return m._traverse(subpath=subpath)
        raise ValueError(
            f"No sub-merkle found for path '{subpath}' in merkle rooted at {self.path}"
        )

    def traverse(self, subpath: Path) -> "Merkle":
        if not subpath.is_absolute():
            subpath = self.path / subpath
        return self._traverse(subpath)

    @staticmethod
    def _get_filename(path: Path) -> Path:
        filename = Path(f"{path.name}.dmerk")
        while filename.exists():
            random_hex_string = "".join(random.choices(string.hexdigits.lower(), k=8))
            filename = Path(f"{path.name}_{random_hex_string}.dmerk")
        return filename

    def save(self, filename: str | Path | None = None) -> str | Path:
        if filename is None:
            filename = Merkle._get_filename(self.path)
        with open(filename, mode="w", encoding="utf-8") as file:
            json.dump(self, file, default=Merkle.json_encode, ensure_ascii=False)
        print(f"Saved merkle for path: '{self.path}' to file: '{filename}'")
        return filename

    @staticmethod
    def load(filename: str | Path) -> "Merkle":
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
            if "children" in output:
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
            if "children" in obj:
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
