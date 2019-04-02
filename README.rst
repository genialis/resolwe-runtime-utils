=========================
Resolwe Runtime Utilities
=========================

|build| |coverage| |docs| |pypi_version| |pypi_pyversions|

.. |build| image:: https://travis-ci.org/genialis/resolwe-runtime-utils.svg?branch=master
    :target: https://travis-ci.org/genialis/resolwe-runtime-utils
    :alt: Build Status

.. |coverage| image:: https://img.shields.io/codecov/c/github/genialis/resolwe-runtime-utils/master.svg
    :target: http://codecov.io/github/genialis/resolwe-runtime-utils?branch=master
    :alt: Coverage Status

.. |docs| image:: https://readthedocs.org/projects/resolwe-runtime-utils/badge/?version=latest
    :target: http://resolwe-runtime-utils.readthedocs.io/
    :alt: Documentation Status

.. |pypi_version| image:: https://img.shields.io/pypi/v/resolwe-runtime-utils.svg
    :target: https://pypi.python.org/pypi/resolwe-runtime-utils
    :alt: Version on PyPI

.. |pypi_pyversions| image:: https://img.shields.io/pypi/pyversions/resolwe-runtime-utils.svg
    :target: https://pypi.python.org/pypi/resolwe-runtime-utils
    :alt: Supported Python versions

A project that provides convenience utilities for writing processes for the
Resolwe_ dataflow engine.

The ``import_file`` function requires `7z` in path.

You can find more information in the documentation_.

.. _Resolwe: https://github.com/genialis/resolwe
.. _documentation: http://resolwe-runtime-utils.readthedocs.io/

Getting started
---------------

Install Resolwe Runtime Utilities from PyPI_::

    pip install resolwe-runtime-utils

Use them in your Python Resolwe process:

.. code-block:: python

    from resolwe_runtime_utils import info, save_file

    info('Some info')
    save_file('etc', 'foo.py')

Or use them in your Bash Resolwe process::

    re-info "Some info"
    re-save-file "etc" "foo.py"

.. _PyPI: https://pypi.python.org/pypi/resolwe-runtime-utils

Contribute
----------

We welcome new contributors. To learn more, read Contributing_ section of our
documentation.

.. _Contributing: http://resolwe-runtime-utils.readthedocs.io/en/latest/contributing.html
