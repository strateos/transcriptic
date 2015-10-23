from setuptools import setup

setup(
    name='transcriptic',
    version='2.0.0',
    packages=['transcriptic'],
    setup_requires=['numpy'],
    install_requires=[
        'Click>=5.1',
        'requests',
        'autoprotocol>=2.5',
        'pandas>=0.16',
        'matplotlib>=1.4',
        'scipy>=0.16',
        'numpy>=1.10'
    ],
    entry_points='''
        [console_scripts]
        transcriptic=transcriptic.cli:cli
    '''
)
