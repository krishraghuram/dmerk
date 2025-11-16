import enum
import json
import logging
import pathlib
import random
import string
from pathlib import Path, PurePath
from typing import Any, Dict


class Merkle:
    __slots__ = ("path", "type", "size", "digest", "_children_data", "_children")
    SLOTS = ("path", "type", "size", "digest", "children")

    class Type(enum.Enum):
        FILE = "file"
        DIRECTORY = "directory"
        SYMLINK = "symlink"

        def __repr__(self) -> str:
            return str(self)

    def __init__(
        self,
        path: PurePath | Path,
        type: Type,
        size: int,
        digest: str,
        # typing.Self only available from 3.11
        children: dict[Path, "Merkle"] | None = None,
        _children_data: dict[str, Any] | None = None,
    ) -> None:
        # Make paths absolute and pure
        if isinstance(path, Path):
            pure_path = PurePath(path.absolute() if not path.is_absolute() else path)
        else:
            if not path.is_absolute():
                raise ValueError(f"Cannot handle non-absolute PurePath {path} !!!")
            pure_path = path
        if children:
            pure_children = {
                PurePath(k.absolute() if not k.is_absolute() else k): v
                for k, v in children.items()
            }
        else:
            pure_children = None
        self.path = pure_path
        self.type = type
        self.size = size
        self.digest = digest
        self._children = pure_children
        if not self._children:
            self._children_data = _children_data

    @property
    def children(self) -> Dict[PurePath, "Merkle"]:
        """Lazily deserialize children only when accessed."""
        if self._children is None:
            if self._children_data is not None:
                PosixPath = pathlib.PosixPath  # noqa: F841
                WindowsPath = pathlib.WindowsPath  # noqa: F841
                PurePosixPath = pathlib.PurePosixPath  # noqa: F841
                PureWindowsPath = pathlib.PureWindowsPath  # noqa: F841
                PurePath = pathlib.PurePath  # noqa: F841
                globs = globals()
                locs = locals()
                self._children = {
                    PurePath(eval(k, globs, locs)): Merkle.from_dict(v)
                    for k, v in self._children_data.items()
                }
                self._children_data = None  # free memory
            else:
                self._children = {}
        return self._children

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Merkle":
        """Create a Merkle instance from a dictionary without processing children."""
        if "__merkle__" not in data:
            logging.error("Not a valid Merkle dictionary")
            raise ValueError("Not a valid Merkle dictionary")
        PosixPath = pathlib.PosixPath  # noqa: F841
        WindowsPath = pathlib.WindowsPath  # noqa: F841
        PurePosixPath = pathlib.PurePosixPath  # noqa: F841
        PureWindowsPath = pathlib.PureWindowsPath  # noqa: F841
        PurePath = pathlib.PurePath  # noqa: F841
        Type = cls.Type  # noqa: F841
        path = PurePath(eval(data["path"]))
        type_data = data["type"]
        if isinstance(type_data, dict) and "__merkle_type__" in type_data:
            try:
                type_val = eval(type_data["__merkle_type__"])
            except AttributeError:
                logging.error("Not a valid Merkle.Type dictionary")
                raise ValueError("Not a valid Merkle.Type dictionary")
        else:
            logging.error("Not a valid Merkle.Type dictionary")
            raise ValueError("Not a valid Merkle.Type dictionary")

        children_data = data.get("children")

        return Merkle(
            path=path,
            type=type_val,
            size=data["size"],
            digest=data["digest"],
            _children_data=children_data,
        )

    def __hash__(self) -> int:
        return hash(
            tuple(
                getattr(self, slotname, None)
                for slotname in set(Merkle.SLOTS) - {"path", "children"}
            )
        )

    def __eq__(self, other: Any) -> bool:
        """
        Return True if self is equal to other, else False

        Note that we do a shallow comparison.
        That is, we also do not compare children, because that would defeat the purpose of lazy loading.
        This should be good enough, because if you think about it,
        two merkles are only really equal if they have same digest.

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
                    for slotname in set(Merkle.SLOTS) - {"path", "children"}
                ]
            )

    def __repr__(self) -> str:
        kwargs = {
            slotname: getattr(self, slotname)
            for slotname in Merkle.SLOTS
            if hasattr(self, slotname)
        }
        argstring = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
        return f"{type(self).__name__}({argstring})"

    def __str__(self) -> str:
        return json.dumps(self, default=Merkle.json_encode, ensure_ascii=False)

    def _traverse(self, subpath: PurePath) -> "Merkle":
        subpath = PurePath(subpath)
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

    def traverse(self, subpath: PurePath) -> "Merkle":
        subpath = PurePath(subpath)
        if not subpath.is_absolute():
            subpath = self.path / subpath
        return self._traverse(subpath)

    @staticmethod
    def _get_filename(path: str, prefix: Path | None = None) -> Path:
        if prefix is None:
            prefix = Path.cwd()
        filename = prefix / Path(f"{path}.dmerk")
        while filename.exists():
            random_hex_string = "".join(random.choices(string.hexdigits.lower(), k=8))
            filename = prefix / Path(f"{path}_{random_hex_string}.dmerk")
        return filename

    def save(self, filename: str | Path | None = None) -> str | Path:
        if filename is None:
            filename = Merkle._get_filename(self.path.name)
        else:
            if isinstance(filename, str):
                filename = Path(filename)
            if filename.is_dir():
                filename = Merkle._get_filename(self.path.name, prefix=filename)
        with open(filename, mode="w", encoding="utf-8") as file:
            json.dump(self, file, default=Merkle.json_encode, ensure_ascii=False)
        logging.info(f"Saved merkle for path: '{self.path}' to file: '{filename}'")
        return filename

    @staticmethod
    def load(filename: str | Path) -> "Merkle":
        with open(filename, mode="r", encoding="utf-8") as file:
            file_content = file.read()
            merkle_dict = json.loads(file_content)
            return Merkle.from_dict(merkle_dict)

    @staticmethod
    def json_encode(obj: Any) -> dict[str, Any]:
        if isinstance(obj, Merkle):
            output = {
                slotname: getattr(obj, slotname)
                for slotname in Merkle.SLOTS
                if hasattr(obj, slotname)
            }
            output["__merkle__"] = True  # To make deserialization work :)
            # Need the below hack because of https://github.com/python/cpython/issues/63020
            output["path"] = repr(PurePath(output["path"]))
            if "children" in output:
                output["children"] = {
                    repr(PurePath(k)): v for k, v in output["children"].items()
                }
            return output
        elif isinstance(obj, Merkle.Type):
            return {"__merkle_type__": str(obj)}
        raise TypeError(f"Object of type {type(obj)} are not JSON serializable")
