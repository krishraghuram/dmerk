import re
import pathlib

import nox

# Usage: nox --session <session-name>
# Example: nox --session lint


@nox.session()
def lint(session):
    session.install("flake8")
    session.run("flake8", "--select=F", "dmerk")


@nox.session()
def format(session):
    session.install("black")
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
    session.install("mypy")
    # TODO: enable mypy for tests as well
    # session.run("mypy", "--strict", "--allow-redefinition", "dmerk")
    session.run(
        "mypy", "--strict", "--allow-redefinition", "--exclude", "test", "dmerk"
    )


@nox.session(
    python=[
        "/usr/bin/python3.10",
        "/home/raghuram/Workspace/bin/Python-3.9.16/python",
        "/home/raghuram/Workspace/bin/Python-3.11.2/python",
        "/home/raghuram/Workspace/bin/pypy3.9-v7.3.11-linux64/bin/pypy",
    ]
)
def test(session):
    session.install("coverage", "pytest")
    session.install(".")
    session.run("coverage", "run", "-m", "pytest", "-x", "-m", "not slow")
    session.run("coverage", "html", "--skip-empty", "--omit=dmerk/test/*")
    print(
        "Coverage HTML Report: "
        + "file://"
        + str(pathlib.Path("htmlcov/index.html").absolute())
    )


@nox.session()
def profile(session):
    session.install("pytest")
    session.install(".")
    session.run("pytest", "-sm", "profile")
