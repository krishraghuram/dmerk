import re
import pathlib

import nox

@nox.session()
def lint(session):
    session.install("pyflakes")
    session.run("pyflakes", "dmerk")

@nox.session()
def format(session):
    session.install("black")
    out = session.run("black", "dmerk", silent=True)
    match = re.search(r"(\d*?)(?: files reformatted, )?(\d*?) files left unchanged.", out)
    if int(match.groups()[0] or 0)>0:  # https://stackoverflow.com/a/46254991/5530864
        raise Exception(f"black has formatted {int(match.groups()[0])} files, please check them")

@nox.session(python=["3.8", "3.10", "3.11"])
def test(session):
    session.install("coverage", "pytest")
    session.install(".")
    session.run("coverage", "run", "-m", "pytest")
    session.run("coverage", "html", "--skip-empty", "--omit=dmerk/test/*")
    print("Coverage HTML Report: " + "file://" + str(pathlib.Path("htmlcov/index.html").absolute()))
