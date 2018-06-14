def get_version(filename):
    from re import findall
    with open(filename) as f:
        metadata = dict(findall(r"__([a-z]+)__ = '([^']+)'", f.read()))
    return metadata['version']


project = 'cachetools'
copyright = '2014-2018 Thomas Kemmer'
version = get_version(b'../cachetools/__init__.py')
release = version

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.todo'
]
exclude_patterns = ['_build']
master_doc = 'index'
html_theme = 'sphinx_rtd_theme'
