import os.path, codecs, re

from setuptools import setup


with codecs.open(os.path.join(os.path.dirname(__file__), 'cachetools', '__init__.py'),
                 encoding='utf8') as f:
    metadata = dict(re.findall(r"__([a-z]+)__ = '([^']+)", f.read()))


setup(
    name='cachetools',
    version=metadata['version'],
    author='Thomas Kemmer',
    author_email='tkemmer@computer.org',
    url='https://github.com/tkem/cachetools',
    license='MIT',
    description='Extensible memoizing collections and decorators',
    long_description=open('README.rst').read(),
    keywords='cache caching memoize memoizing memoization LRU LFU TTL',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    packages=['cachetools'],
    test_suite='tests'
)
