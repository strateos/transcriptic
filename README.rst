Transcriptic Python Library
===========================

|PyPI Version| |Build Status| |Documentation| |Code Coverage| |Downloads| |Binder|

The Transcriptic Python Library (TxPy) provides a Python interface for
managing Transcriptic organizations, projects, runs, datasets and more.
One can either interface with our library through the bundled command
line interface (CLI) or through a Jupyter notebook using a Python
client.

We recommend using the Jupyter interface as it provides a nice rendering
and presentation of the objects, as well as provide additional analysis
and properties functions specific to the Transcriptic objects.

Transcriptic is the robotic cloud laboratory for the life sciences.
https://www.transcriptic.com

Setup
-----

Organization
~~~~~~~~~~~~

TxPy is separated into three main components: 1) Core. The core modules
provide a barebones client for making calls to the Transcriptic webapp
to create and obtain data. This can be done via the ``api`` object or
via the command-line using the CLI. 2) Jupyter. This module provides a
Jupyter-centric means for interacting with objects returned from the
Transcriptic webapp such as Run, Project and Dataset. 3) Analysis. This
module provides some basic analysis wrappers around datasets returned
from the webapp using standard Python scientific libraries.

Installation
~~~~~~~~~~~~

For a barebones CLI install, you’ll do:

.. code-block:: bash

   pip install transcriptic

We recommend installing the ``jupyter`` module for Jupyter-centric
navigation:

.. code-block:: bash

   pip install transcriptic[jupyter]

Lastly, we recommend installing the ``analysis`` module for a
full-fledged experience:

.. code-block:: bash

   pip install transcriptic[analysis]

Alternatively, if you’re interested in contributing or living at the
edge:

.. code-block:: bash

   git clone https://github.com/strateos/transcriptic.git
   cd transcriptic
   pip install .[jupyter,analysis]

to upgrade to the latest version using pip or check whether you’re
already up to date:

.. code-block:: bash

   pip install transcriptic --upgrade

Then, login to your Transcriptic account:

.. code-block:: bash

   $ transcriptic login
   Email: me@example.com
   Password:
   Logged in as me@example.com (example-lab)

Tab Completion
~~~~~~~~~~~~~~

To enable auto-completion for the Transcriptic CLI, you’ll need to
download an appropriate auto-complete file and add it your shell
configuration.

Here’s an example script for installing it on a bash shell in your
``~/.config`` directory.

.. code-block:: bash

   export INSTALL_DIR=~/.config && mkdir -p $INSTALL_DIR
   curl -L https://raw.githubusercontent.com/strateos/transcriptic/master/autocomplete/bash.sh > $INSTALL_DIR/tx_complete.sh && chmod +x $INSTALL_DIR/tx_complete.sh
   echo ". $INSTALL_DIR/tx_complete.sh" >> ~/.bash_profile

-  Ubuntu and Fedora note: Modify your ``~/.bashrc`` instead of
   ``~/.bash_profile``
-  Zsh note: Use ``autocomplete/zsh.sh`` instead of ``bash.sh``. Modify
   your ``~/.zshrc`` instead of ``~/.bash_profile``
-  Fish note: Use ``autocomplete/fish.sh`` instead of ``bash.sh``.
   Change ``$INSTALL_DIR`` to ``~/.config/fish/completions`` and rename
   ``tx-complete.sh`` to ``tx-complete.fish``. Skip the last step.

Documentation
-------------

CLI
~~~

See the `Transcriptic Developer
Documentation <https://developers.strateos.com/docs/getting-started-with-the-cli>`__
for detailed information about how to use this package, including
learning about how to package protocols and build releases.

Jupyter
~~~~~~~

Click on the |Binder| icon to open an interactive notebook environment
for using the library.

Developer
~~~~~~~~~

View `Developer Specific
Documentation <http://transcriptic.readthedocs.io/en/latest/>`__

Permissions
-----------

Note that direct analysis and submission of Autoprotocol is currently
restricted. Please contact sales@strateos.com if you would like to do
so.

Contributing
------------

Read `Contributing <http://transcriptic.readthedocs.io/en/latest/contributing.html>`__ for more information on contributing to TxPy.

.. |PyPI Version| image:: https://img.shields.io/pypi/v/transcriptic.svg?maxAge=86400
   :target: https://pypi.python.org/pypi/transcriptic
.. |Build Status| image:: https://github.com/strateos/transcriptic/workflows/CI/badge.svg?branch=master
   :target: https://github.com/strateos/transcriptic/actions?query=workflow%3ACI+branch%3Amaster
.. |Documentation| image:: https://readthedocs.org/projects/transcriptic/badge/?version=latest
   :target: http://transcriptic.readthedocs.io/en/latest/?badge=latest
.. |Code Coverage| image:: https://codecov.io/gh/strateos/transcriptic/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/strateos/transcriptic
.. |Downloads| image:: https://img.shields.io/pypi/dm/transcriptic?logo=pypi
   :target: https://transcriptic.readthedocs.io/en/latest
.. |Binder| image:: https://mybinder.org/badge_logo.svg
   :target: https://mybinder.org/v2/gh/strateos/transcriptic/master?urlpath=git-pull%3Frepo%3Dhttps%253A%252F%252Fgithub.com%252Fopen-strateos%252Ftxpy_jupyter_notebooks%26urlpath%3Dtree%252Ftxpy_jupyter_notebooks%252Findex.ipynb%26branch%3Dmain
