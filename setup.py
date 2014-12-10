from setuptools import setup

setup(
    name='transcriptic',
    version='1.0.0',
    py_modules=['transcriptic'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        transcriptic=transcriptic:cli
    ''',
)
