from setuptools import setup

setup(
    name='ap2en',
    version='1.0.0',
    py_modules=['ap2en'],
    install_requires=[
        'autoprotocol'
    ],
    entry_points='''
        [console_scripts]
        ap2en = ap2en:parse
    ''',
)
