#!/usr/bin/env python
from setuptools import setup
import sys

# Load version
exec(open('transcriptic/version.py').read())

if sys.version_info[:2] < (2, 6) or (3, 0) <= sys.version_info[0:2] < (3, 3):
    raise RuntimeError("Python version 2.6, 2.7 or >= 3.3 required.")

setup(
    name='transcriptic',
    description='Transcriptic CLI & Python Client Library',
    url='https://github.com/transcriptic/transcriptic',
    version=__version__,
    packages=['transcriptic', 'transcriptic.analysis'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest>=2.9.0', 'tox>=2.3.1'],
    install_requires=[
        'Click>=5.1',
        'requests',
        'autoprotocol>=3.4',
        'pandas>=0.18',
        'matplotlib>=1.4',
        'scipy>=0.16',
        'numpy>=1.10',
        'plotly>=1.9.6',
        'pillow>=3.1.0',
        'future>=0.15'
    ],
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
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ]
)
