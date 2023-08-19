import dmerk.generate as generate
from dmerk.merkle import Merkle


def load_or_generate(path, no_save):
    if path.is_file() and path.name.endswith(".dmerk"):
        merkle = Merkle.load(path)
    else:
        merkle = generate.generate(path)
        if not no_save:
            merkle.save()
    return merkle
