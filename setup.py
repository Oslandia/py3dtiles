# -*- coding: utf-8 -*-
import os
import re
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))


requirements = (
    'numpy',
    'pyproj'
)

dev_requirements = (
    'pytest',
    'pytest-cov',
)

doc_requirements = (
    'sphinx',
    'sphinx_rtd_theme',
)

prod_requirements = (
)


def find_version(*file_paths):
    """
    see https://github.com/pypa/sampleproject/blob/master/setup.py
    """

    with open(os.path.join(here, *file_paths), 'r') as f:
        version_file = f.read()

    # The version line must have the form
    # __version__ = 'ver'
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string. "
                       "Should be at the first line of __init__.py.")


setup(
    name='py3dtiles',
    version=find_version('py3dtiles', '__init__.py'),
    description="Python module for 3D tiles format",
    url='https://github.com/Oslandia/py3dtiles',
    author='dev',
    author_email='contact@oslandia.com',
    license='LGPL-2.1',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    packages=find_packages(),
    install_requires=requirements,
    test_suite="tests",
    scripts=["tools/py3dtiles_info"],
    extras_require={
        'dev': dev_requirements,
        'prod': prod_requirements,
        'doc': doc_requirements
    }
)
