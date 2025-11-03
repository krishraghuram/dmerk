import dmerk.generate as generate
from dmerk.merkle import Merkle
from pathlib import Path
import colorsys


def load_or_generate(path: Path, no_save: bool) -> Merkle:
    if path.is_file() and path.name.endswith(".dmerk"):
        merkle = Merkle.load(path)
    else:
        merkle = generate.generate(path)
        if not no_save:
            merkle.save()
    return merkle


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


def fuzzy_match(text: str, query: str | None = None) -> bool:
    # TODO: Implement actual fuzzy matching
    if query:
        return query.casefold() in text.casefold()
    else:
        return True
