import os

from setuptools import Extension, setup


HERE = os.path.dirname(__file__)
CACHETOOLS_ROOT = os.path.join(HERE, 'cachetools')


# TODO: If we start implementing this library (or parts of it) in Cython,
# change this to .pyx.
file_extension = '.py'


def replace_extensions(sources):
    return [os.path.splitext(f)[0] + file_extension for f in sources]


if os.getenv('CACHETOOLS_USE_CYTHON'):
    try:
        from Cython.Build import cythonize
        HAVE_CYTHON = True
    except ImportError:
        print(
            'The CACHETOOLS_USE_CYTHON environment variable was defined but'
            " Cython isn't installed. Package installation will proceed"
            'without it.'
        )
        HAVE_CYTHON = False
else:
    HAVE_CYTHON = False


if HAVE_CYTHON:
    modules = [
        Extension(
            ('cachetools.' + os.path.splitext(f)[0]),
            replace_extensions([os.path.join(CACHETOOLS_ROOT, f)])
        )
        for f in os.listdir(CACHETOOLS_ROOT)
        if f.endswith('.py')
    ]
    extra = {'ext_modules': cythonize(modules, language_level=3)}
else:
    extra = {}


setup(**extra)
