from pathlib import PosixPath
import importlib


def test_generate_proxy(monkeypatch):
    generate = importlib.reload(importlib.import_module("dmerk.generate"))
    called = False

    def mock_default_generate(directory, continue_on_error=False):
        nonlocal called
        called = True

    monkeypatch.setattr(generate, "default_generate", mock_default_generate)

    assert called is False
    generate.generate(PosixPath("."))
    assert called is True


def test_hashlib_backport(monkeypatch):
    """
    Verify that hashlib.file_digest is backported with dmerk.generate.hashlib_file_digest.file_digest if needed
    """
    hashlib = importlib.reload(importlib.import_module("hashlib"))
    if hasattr(hashlib, "file_digest"):
        hashlib_file_digest = importlib.reload(
            importlib.import_module("dmerk.generate.hashlib_file_digest")
        )
        assert hashlib.file_digest is not hashlib_file_digest.file_digest
        monkeypatch.delattr(hashlib, "file_digest")
    importlib.reload(importlib.import_module("dmerk.generate.default"))
    assert hashlib.file_digest is hashlib_file_digest.file_digest
