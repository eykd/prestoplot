import os
import sys

from setuptools import setup

sys.path.insert(0, os.path.dirname(__file__))

import versioneer  # noqa: E402

setup(version=versioneer.get_version(), cmdclass=versioneer.get_cmdclass())
