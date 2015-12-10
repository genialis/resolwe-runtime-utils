=========================
Resolwe runtime utilities
=========================

.. image:: https://readthedocs.org/projects/resolwe-runtime-utils/badge/?version=latest
    :target: http://resolwe-runtime-utils.readthedocs.org/
    :alt: Latest Docs

A project that provides convenience utilities for writing processes for the
Resolwe_ dataflow engine.

You can find more information in the documentation_.

.. _Resolwe: https://github.com/genialis/resolwe
.. _documentation: http://resolwe-runtime-utils.readthedocs.org/

Getting started
---------------

Install resolwe-runtime-utils from PyPI_::

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
