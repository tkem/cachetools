import pathlib
import sys

basedir = pathlib.Path(__file__).parent.parent

sys.path.insert(0, str((basedir / "src").resolve()))


def get_version():
    import configparser

    cp = configparser.ConfigParser()
    cp.read(basedir / "setup.cfg")
    return cp["metadata"]["version"]


project = "cachetools"
copyright = "2014-2022 Thomas Kemmer"
version = get_version()
release = version

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.todo",
]
exclude_patterns = ["_build"]
master_doc = "index"
html_theme = "default"
