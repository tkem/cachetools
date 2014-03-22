from setuptools import setup


def get_version(filename):
    import re
    content = open(filename).read()
    metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", content))
    return metadata['version']

setup(
    name='cachetools',
    version=get_version('cachetools.py'),
    author='Thomas Kemmer',
    author_email='tkemmer@computer.org',
    url='https://github.com/tkem/cachetools',
    license='MIT',
    description='Python 2.7 memoizing collections and decorators',  # noqa
    long_description=open('README.rst').read(),
    keywords='cache caching lru lfu ttl',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    py_modules=['cachetools'],
    test_suite='nose.collector',
    tests_require=['nose']
)
