# ![](https://www.transcriptic.com/images/logo-transcriptic-blobs-880e2f7b.svg) Transcriptic Python Library

The Transcriptic Python Library (TxPy) provides a Python interface for managing Transcriptic organizations, projects, runs, datasets and more.
One can either interface with our library through the bundled command line interface (CLI) or through a Jupyter notebook.

We recommend using the Jupyter interface as it provides a nice rendering and presentation of the objects, as well as provide
additional analysis and properties functions specific to the Transcriptic objects.

Transcriptic is the robotic cloud laboratory for the life sciences. [https://www.transcriptic.com](https://www.transcriptic.com)

## Setup

```
$ pip install transcriptic
```

or

```
$ git clone https://github.com/transcriptic/transcriptic.git
$ cd transcriptic
$ pip install .
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

## Documentation

See the [Transcriptic Developer Documentation](https://developers.transcriptic.com/docs/getting-started-with-the-cli) for detailed information about how to use this package, including learning about how to package protocols and build releases.

View [developer specific documentation](http://transcriptic.readthedocs.io/en/latest/)

## Contributing

Read CONTRIBUTING.mmd for more information on contributing to TxPy
