#!/usr/bin/env python3
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

# Load version
exec(open('transcriptic/version.py').read())


# Test Runner (reference: https://docs.pytest.org/en/latest/goodpractices.html)
class PyTest(TestCommand):
    user_options = [("pytest-args=", "a", "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = "--cov=transcriptic --cov-report=term"

    def run_tests(self):
        import shlex

         # import here, cause outside the eggs aren't loaded
        import pytest

        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


# Test and Documentation dependencies
test_deps = [
    'coverage>=4.5, <5',
    'jsonschema>=2.6, <3',
    'mock>=3, <4',
    'pylint>=1.9, <2',
    'pytest>=4, <5',
    'pytest-cov>=2, <3',
    'tox>=3.7, <4'
]

doc_deps = [
    'releases>=1.5, <2',
    'mock>=3, <4',
    'Sphinx>=1.7, <1.8',
    'sphinx_rtd_theme>=0.4, <1'
]

# Extra module dependencies
jupyter_deps = [
    'pandas>=0.23,<1'
]

analysis_deps = [
    'pandas>=0.23,<1',
    'matplotlib>=1.4, <2',
    'scipy>=0.14, <1',
    'numpy>=1.14, <2',
    'plotly==1.9.6',
    'pillow>=3, <4'
]


setup(
    name='transcriptic',
    description='Transcriptic CLI & Python Client Library',
    url='https://github.com/transcriptic/transcriptic',
    version=__version__,
    packages=['transcriptic', 'transcriptic.jupyter', 'transcriptic.analysis'],
    include_package_data=True,
    tests_require=test_deps,
    python_requires='>=3.5',
    install_requires=[
        'Click>=7.0,<8',
        'requests>=2.0,<3',
        'python-magic>=0.4,<1',
        'Jinja2>=2.0,<3',
    ],
    extras_require={
        'jupyter': jupyter_deps,
        'analysis': analysis_deps,
        'docs': doc_deps,
        'test': test_deps
    },
    cmdclass={"pytest": PyTest},
    entry_points='''
        [console_scripts]
        transcriptic=transcriptic.cli:cli
    ''',
    license='BSD',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ]
)
