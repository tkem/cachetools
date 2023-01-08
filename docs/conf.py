import pathlib
import sys

basedir = pathlib.Path(__file__).parent.parent

sys.path.insert(0, str((basedir / "src").resolve()))

project = "cachetools"
copyright = "2014-2023 Thomas Kemmer"
version = "5.2"
release = "5.2.1"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.todo",
]
exclude_patterns = ["_build"]
master_doc = "index"
html_theme = "default"
