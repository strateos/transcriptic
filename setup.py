#!/usr/bin/env python
from setuptools import setup
import sys

# Load version
exec(open('transcriptic/version.py').read())

if sys.version_info[:2] < (2, 7) or (3, 0) <= sys.version_info[0:2] < (3, 5):
    raise RuntimeError("Python version 2.7 or >= 3.5 required.")

setup(
    name='transcriptic',
    description='Transcriptic CLI & Python Client Library',
    url='https://github.com/transcriptic/transcriptic',
    version=__version__,
    packages=['transcriptic', 'transcriptic.jupyter', 'transcriptic.analysis'],
    setup_requires=['pytest-runner'],
    include_package_data=True,
    tests_require=[
        'coverage==4.*',
        'future>=0.15',
        'jsonschema>=2.5',
        'mock>=2.*',
        'pylint==1.*',
        'pytest==3.*',
        'tox==3.*'
    ],
    install_requires=[
        'Click>=5.1',
        'requests>=2.0',
        'future>=0.15',
        'python-magic>=0.4.13',
        'Jinja2>=2.7,<3',
    ],
    extras_require={
        'jupyter': [
            'pandas>=0.18'
        ],
        'analysis': [
            'pandas>=0.18',
            'matplotlib>=1.4',
            'scipy>=0.16',
            'numpy>=1.10',
            'plotly==1.9.6',
            'pillow>=3.1.0'
        ]
    },
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
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ],
)
