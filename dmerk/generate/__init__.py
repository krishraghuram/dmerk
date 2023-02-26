from .default import generate as default_generate


def generate(*args, **kwargs):
    # Can add platform-specific impl here if needed (for cross-platform compatibility or performance reasons)
    return default_generate(*args, **kwargs)
