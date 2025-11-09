"""
Usage: nox --session <session-name>
Examples:
  nox --session lint
  nox --session format
  nox --session mypy
  nox --session test
  nox --session test_performance
  nox --session profile
"""

import re
import pathlib
import subprocess

import nox

# TODO: hardcoded paths, not portable
PYTHON_VERSIONS = [
    "/usr/bin/python3.10",
    "/home/raghuram/Workspace/bin/pypy3.10-v7.3.12-linux64/bin/pypy",
    "/home/raghuram/Workspace/bin/Python-3.11.2/python",
]


@nox.session()
def lint(session):
    session.install(".[dev]")
    session.run("flake8", "--select=F", "dmerk")


@nox.session()
def isort(session):
    session.install(".[dev]")
    session.run("isort", "dmerk")


@nox.session()
def format(session):
    session.install(".[dev]")
    out = session.run("black", "dmerk", silent=True)
    match = re.search(
        r"(\d*?)(?: files? reformatted, )?(\d*?) files? left unchanged.", out
    )
    if int(match.groups()[0] or 0) > 0:  # https://stackoverflow.com/a/46254991/5530864
        raise Exception(
            f"black has formatted {int(match.groups()[0])} files, please check them"
        )


@nox.session()
def mypy(session):
    session.install(".[dev]")
    # TODO: enable mypy for tests as well
    # session.run("mypy", "--strict", "--allow-redefinition", "dmerk")
    session.run(
        "mypy", "--strict", "--allow-redefinition", "--exclude", "test", "dmerk"
    )


@nox.session(python=PYTHON_VERSIONS)
def test(session):
    try:
        session.install(".[dev]")
        session.run("coverage", "run", "-m", "pytest", "-x", "-m", "not slow")
        # TODO: Re-enable coverage check for dmerk/tui/* after adding textual tests
        # Textual Testing: https://textual.textualize.io/guide/testing/
        session.run(
            "coverage",
            "html",
            "--fail-under=95",
            "--skip-empty",
            "--omit=dmerk/test/*,dmerk/tui/*,**/hashlib_file_digest.py",
        )
    except Exception:
        raise
    finally:
        coverage_file_url = (
            f"file://{str(pathlib.Path('htmlcov/index.html').absolute())}"
        )
        print(f"Coverage HTML Report: {coverage_file_url}")
        subprocess.run(["open", coverage_file_url])


@nox.session(python=PYTHON_VERSIONS)
def test_performance(session):
    session.install(".[dev]")
    session.run("pytest", "-sm", "test_performance")


@nox.session()
def profile(session):
    session.install(".[dev]")
    session.run("pytest", "-sm", "profile")
