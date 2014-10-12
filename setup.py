from setuptools import setup


def get_version(filename):
    import re
    content = open(filename).read()
    metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", content))
    return metadata['version']

setup(
    name='cachetools',
    version=get_version('cachetools/__init__.py'),
    author='Thomas Kemmer',
    author_email='tkemmer@computer.org',
    url='https://github.com/tkem/cachetools',
    license='MIT',
    description='Extensible memoizing collections and decorators',  # noqa
    long_description=open('README.rst').read(),
    keywords='cache caching LRU LFU TTL',
    classifiers=[
        'Development Status :: 4 - Beta',
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
