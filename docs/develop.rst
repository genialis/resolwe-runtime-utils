-------
Develop
-------

Preparing environement
----------------------

`Fork <https://help.github.com/articles/fork-a-repo>`__ the main
`resolwe-runtime-utils's git repository
<https://github.com/genialis/resolwe>`_.

If you don't have Git installed on your system, follow `these
instructions <http://git-scm.com/book/en/v2/Getting-Started-Installing-Git>`__.

Clone your fork (replace ``<username>`` with your GitHub account name) and
change directory::

    git clone https://github.com/<username>/resolwe-runtime-utils.git
    cd resolwe-runtime-utils

Prepare Resolwe for development::

    pip install -e .[docs,package,test]

.. note::

    We recommend using `pyvenv <http://docs.python.org/3/library/venv.html>`_
    to create an isolated Python environement for resolwe-runtime-utils.

Running tests
-------------

To run the tests, use::

    python setup.py test

To run the tests with Tox_, use::

    tox -r

.. _Tox: http://tox.testrun.org/

Buildling documentation
-----------------------

.. code-block:: none

    python setup.py build_sphinx

Preparing release
-----------------

Clean ``build`` directory::

    python setup.py clean -a

Remote previous distributions in ``dist`` directory::

    rm dist/*

Bump project's version in ``__about__.py`` file and commit changes to git.

.. note::

    Use `Semantic versioning`_.

Create source distribution::

    python setup.py sdist

Build wheel::

    python setup.py bdist_wheel

Upload distribution to PyPI_::

    twine upload dist/*

.. _Semantic versioning: https://packaging.python.org/en/latest/distributing/#semantic-versioning-preferred
.. _PyPI: https://pypi.python.org/pypi/resolwe-runtime-utils
