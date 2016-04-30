
Installation
------------

.. code-block:: shell

    $ pip install transcriptic

or

.. code-block:: shell

    $ git clone https://github.com/transcriptic/transcriptic.git
    $ cd transcriptic
    $ pip install .


to upgrade to the latest version using pip or check whether you're already up to date:

.. code-block:: shell

    $ pip install transcriptic --upgrade


Then, login to your Transcriptic account:

.. code-block:: shell

    $ transcriptic login
    Email: me@example.com
    Password:
    Logged in as me@example.com (example-lab)


Overview
--------

When using the command line interface (CLI), you can use `transcriptic --help` to understand the function
arguments and effect of each function.

We recommend using Jupyter notebooks to interface with the Transcriptic library. To do so, we recommend using
the `transcriptic.object` and `transcriptic.analysis` modules to load and analyze data.
For more advanced users, please refer to the `transcriptic.config` module for API calls.

Further Documentation
---------------------

See the `Transcriptic Developer Documentation <https://developers.transcriptic.com/docs/getting-started-with-the-cli/>`_ for detailed information about how to use this package, including learning about how to package protocols and build releases.


Contributing
------------

You can find our Github repository at https://github.com/transcriptic/transcriptic
Please read `CONTRIBUTING.md` for more information.