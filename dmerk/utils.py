import dmerk.generate as generate
from dmerk.merkle import Merkle
from pathlib import Path


def load_or_generate(path: Path, no_save: bool) -> Merkle:
    if path.is_file() and path.name.endswith(".dmerk"):
        merkle = Merkle.load(path)
    else:
        merkle = generate.generate(path)
        if not no_save:
            merkle.save()
    return merkle
