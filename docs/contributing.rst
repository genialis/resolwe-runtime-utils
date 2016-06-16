============
Contributing
============

Preparing environment
=====================

`Fork <https://help.github.com/articles/fork-a-repo>`__ the main
|project_git_repo_link|.

If you don't have Git installed on your system, follow `these
instructions <http://git-scm.com/book/en/v2/Getting-Started-Installing-Git>`__.

Clone your fork (replace ``<username>`` with your GitHub account name) and
change directory::

    git clone https://github.com/<username>/resolwe-runtime-utils.git
    cd resolwe-runtime-utils

Prepare |project_name| for development::

    pip install -e .[dev,docs,package,test]

.. note::

    We recommend using `pyvenv <http://docs.python.org/3/library/venv.html>`_
    to create an isolated Python environement for resolwe-runtime-utils.

Running tests
=============

Using Tox_
----------

To run the tests, use::

    tox

To re-create the virtual environment before running the tests, use::

    tox -r

To only run the tests of a given Tox environment, use::

    tox -e <tox-environment>

For example, to only run the packaging tests, use ::

    tox -e packaging

.. note::

    To see the list of available Tox environments, see ``tox.ini``.

.. _Tox: http://tox.testrun.org/


Manually
--------

To run the tests, use::

    py.test

Coverage report
---------------

To see the tests' code coverage, use::

    py.test --cov=resolwe_runtime_utils

To generate a HTML with tests' code coverage, use::

    py.test --cov=resolwe_runtime_utils --cov-report=html

Building documentation
======================

.. code-block:: none

    python setup.py build_sphinx

Preparing release
=================

Clean ``build`` directory::

    python setup.py clean -a

Remote previous distributions in ``dist`` directory::

    rm dist/*

Remove previous ``egg-info`` directory::

    rm -r *.egg-info

Bump project's version in ``__about__.py`` file and update the changelog in
``docs/CHANGELOG.rst``.

.. note::

    Use `Semantic versioning`_.

Commit changes to git::

    git commit -a -m "Prepare release <new-version>"

Test the new version with Tox_::

    tox -r

Create source distribution::

    python setup.py sdist

Build wheel::

    python setup.py bdist_wheel

Upload distribution to PyPI_::

    twine upload dist/*

Tag the new version::

    git tag <new-version>

Push changes to the main |project_git_repo_link|::

   git push <resolwe-upstream-name> master <new-version>

.. _Semantic versioning: https://packaging.python.org/en/latest/distributing/#semantic-versioning-preferred
.. _PyPI: https://pypi.python.org/pypi/resolwe-runtime-utils
