# Contributing

## Structure
The Transcriptic Python Library (TxPy) is separated into two main portions: the command line interface (CLI) and the
Jupyter notebook interface.

Both the CLI and the notebook interface uses the base `Connection` object for making relevant application programming
 interface (API) calls to Transcriptic.
The `Connection` object itself uses the `routes` module to figure out the relevant routes and passes that onto the `api`
module for making these calls.

The base functionality of the CLI is handled by the `cli` module which is the front-facing interface for users. The
`english` module provides autoprotocol parsing functionalities, and the `util` module provides additional generic helper functions.

The base functionality of the notebook interface is exposed through the `objects` module. Additional analysis of these
 objects is provided through the `analysis` module. In general, html representations should be provided as much as possible.

For analysis purposes, we prefer using Pandas DataFrames and NumPy arrays for representing and slicing data. For plotting,
matplotlib and plotly is preferred.


## Version Compatibility
We use the [future](https://pypi.python.org/pypi/future) module to maintain Python 2/3 compatibility. As a result, all
code written should be Python 2.6/2.7 and Python 3.3+ compatible.


## Styling and Documentation
All code written should follow the [PEP8 standard](https://www.python.org/dev/peps/pep-0008/)

For documentation purposes, we follow [NumPy style doc strings](https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt)


## Testing
For testing purposes, we write tests in the `test` folder in the [pytest](http://pytest.org/latest/getting-started.html)
format. We also use [tox](https://tox.readthedocs.org/en/latest/) for automating tests.

Ensure that all tests pass when you run `tox` in the main folder.