from .linux import generate as linux_generate
from .default import generate as default_generate
import sys

def generate(*args, **kwargs):
    if sys.platform.startswith('linux'):
        try:
            out = linux_generate(*args, **kwargs)
        except Exception as e:
            print(f"Got exception '{e}' when trying linux-optimized implementation of generate", file=sys.stderr)
            print(f"Falling back to generic cross-platform implementation of generate", file=sys.stderr)
            out = default_generate(*args, **kwargs)
    else:
        print("Detected non-linux operating system...", file=sys.stderr)
        print("Using generic cross-platform implementation of generate, this is not optimized for speed...", file=sys.stderr)
        print("Go grab a ☕, this might take a while 😞", file=sys.stderr)
        out = default_generate(*args, **kwargs)
    return out
