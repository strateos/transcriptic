
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

In the command line interface (CLI), use `transcriptic --help` for a summary of
arguments and their function.

Transcriptic library objects are developed with Jupyter notebooks in mind and are best utilized
alongside that interface. Use `transcriptic.object` and `transcriptic.analysis` to load and
analyze data respectively.
API calls are located in the `transcriptic.config` module for more advanced connection needs.

Permissions
-----------

Note that direct analysis and submission of Autoprotocol is currently restricted. Please contact sales@transcriptic.com if you would like to do so.


Further Documentation
---------------------

See the `Transcriptic Developer Documentation <https://developers.transcriptic.com/docs/getting-started-with-the-cli/>`_ for detailed information about how to use this package, including learning about how to package protocols and build releases.


Contributing
------------

You can find our Github repository at https://github.com/transcriptic/transcriptic
Please read `CONTRIBUTING.md` for more information.
