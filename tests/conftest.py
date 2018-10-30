import os.path
import sys


def pytest_ignore_collect(path):
    if sys.version_info >= (3, 5):
        # do not skip any file when running tests with 3.5+
        return False

    else:
        # skip async tests when running tests with <3.5
        return 'async' in os.path.basename(str(path))
