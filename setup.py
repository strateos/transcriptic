from setuptools import setup

setup(
    name='transcriptic',
    description='Transcriptic CLI & Python Client Library',
    url='https://github.com/transcriptic/transcriptic',
    version='2.0.3',
    packages=['transcriptic', 'transcriptic.analysis'],
    install_requires=[
        'Click>=5.1',
        'requests',
        'autoprotocol>=2.5',
        'pandas>=0.16',
        'matplotlib>=1.4',
        'scikit-learn>=0.16',
        'scipy>=0.16',
        'numpy>=1.10',
        'plotly>=1.8',
        'future>=0.15'
    ],
    entry_points='''
        [console_scripts]
        transcriptic=transcriptic.cli:cli
    '''
)
