python-opsi Tests
=================

Various testcases for python-opsi exist in the ``tests`` directory.

Running tests
-------------

The easiest way is to use `nose <https://pypi.python.org/pypi/nose/>`_
for collecting and running the tests.


Configuring Backends
--------------------

Some backends require additional configuration.
The configuration for these backends is made in the file
``tests/Backends/config.py``.

There is an example provided that you can copy and modify to match your
setup. You will find it at ``tests/Backends/config.py.example``.

.. warning::
  Please do not use your production settings there because running the
  test suite will probably result in losing your data!
