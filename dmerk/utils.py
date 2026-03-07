import colorsys
import functools
from pathlib import Path

from rapidfuzz import fuzz

import dmerk.generate as generate
from dmerk.merkle import Merkle


def load_or_generate(path: Path, no_save: bool) -> Merkle:
    if path.is_file() and (
        path.name.endswith(".dmerk") or path.name.endswith(".dmerk.gz")
    ):
        merkle = Merkle.load(path)
    else:
        merkle = generate.generate(path)
        if not no_save:
            merkle.save()
    return merkle


@functools.lru_cache(maxsize=1024)
def colorhash(hash_hex_string: str) -> str:
    hash_bytearray = bytearray.fromhex(hash_hex_string)
    hash_binary_string = "".join([f"{i:08b}" for i in hash_bytearray])
    h = int(hash_binary_string[0:64], base=2) / 2**64
    # l = int(hash_binary_string[96:128],base=2)/2**32
    # s = int(hash_binary_string[64:96],base=2)/2**32
    l = 0.6
    s = int(hash_binary_string[64:128], base=2) / 2**64
    return (
        "rgb("
        + ",".join([str(int(255 * i)) for i in colorsys.hls_to_rgb(h, l, s)])
        + ")"
    )


@functools.lru_cache(maxsize=256)
def prefix_symbol_path(path: Path) -> str:
    if path.is_symlink():
        return "🔗 "
    elif path.is_dir():
        return "📁 "
    elif path.is_file():
        return "📄 "
    else:
        return "⭐ "


PREFIX_SYMBOL_MERKLE: dict[Merkle.Type | None, str] = {
    Merkle.Type.SYMLINK: "🔗 ",
    Merkle.Type.DIRECTORY: "📁 ",
    Merkle.Type.FILE: "📄 ",
    None: "⭐ ",
}


def fuzzy_match(text: str, query: str | None = None, threshold: float = 80.0) -> bool:
    """
    Fuzzy match text against query using rapidfuzz.
    If query is None or empty, it matches everything.
    Default threshold is 80.0.
    """
    if not query:
        return True
    score = fuzz.partial_ratio(query.casefold(), text.casefold())
    return score >= threshold
