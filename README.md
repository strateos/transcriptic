# <img src= "https://static-public.transcriptic.com/logos/blobs.svg" width="40" height="40"> Transcriptic Python Library

[![PyPI Version](https://img.shields.io/pypi/v/transcriptic.svg?maxAge=86400)](https://pypi.python.org/pypi/transcriptic)
[![Build Status](https://travis-ci.org/transcriptic/transcriptic.svg?branch=master)](https://travis-ci.org/transcriptic/transcriptic)

The Transcriptic Python Library (TxPy) provides a Python interface for managing Transcriptic organizations, projects, runs, datasets and more.
One can either interface with our library through the bundled command line interface (CLI) or through a Jupyter notebook using a Python client.

We recommend using the Jupyter interface as it provides a nice rendering and presentation of the objects, as well as provide
additional analysis and properties functions specific to the Transcriptic objects.

Transcriptic is the robotic cloud laboratory for the life sciences. [https://www.transcriptic.com](https://www.transcriptic.com)

## Setup

### Organization
TxPy is separated into three main components:
1) Core. The core modules provide a barebones client for making calls to
the Transcriptic webapp to create and obtain data. This can be done via the
`api` object or via the command-line using the CLI.
2) Jupyter. This module provides a Jupyter-centric means for interacting with
objects returned from the Transcriptic webapp such as Run, Project and Dataset.
3) Analysis. This module provides some basic analysis wrappers around datasets
returned from the webapp using standard Python scientific libraries.

### Installation
For a barebones CLI install, you'll do:
```
$ pip install transcriptic
```
We recommend installing the `jupyter` module for Jupyter-centric navigation:
```
$ pip install transcriptic[jupyter]
```
Lastly, we recommend installing the `analysis` module for a full-fledged experience:
```
$ pip install transcriptic[analysis]
```

Alternatively, if you're interested in contributing or living at the edge:
```
$ git clone https://github.com/transcriptic/transcriptic.git
$ cd transcriptic
$ pip install .[jupyter,analysis]
```

to upgrade to the latest version using pip or check whether you're already up to date:
```
$ pip install transcriptic --upgrade
```

Then, login to your Transcriptic account:

```
$ transcriptic login
Email: me@example.com
Password:
Logged in as me@example.com (example-lab)
```

To enable auto tab-completion for the Transcriptic CLI, enter `source transcriptic_bash_complete.sh` into your terminal.
To enable this for every single session automatically, add `. path/to/transcriptic_bash_complete.sh` to your `.bashrc` file.
For zsh users, use `transcriptic_zsh_complete.sh` instead and add that to your `.zshrc` file.

## Documentation

See the [Transcriptic Developer Documentation](https://developers.transcriptic.com/docs/getting-started-with-the-cli) for detailed information about how to use this package, including learning about how to package protocols and build releases.

View [Developer Specific Documentation](http://transcriptic.readthedocs.io/en/latest/)

## Permissions

Note that direct analysis and submission of Autoprotocol is currently restricted. Please contact sales@strateos.com if you would like to do so.

## Contributing

Read `CONTRIBUTING.md` for more information on contributing to TxPy
