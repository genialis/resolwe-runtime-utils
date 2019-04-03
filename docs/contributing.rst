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

Checkout the latest code and create a release branch::

    git checkout master
    git pull
    git checkout -b release-<new-version>

Replace the *Unreleased* heading in ``docs/CHANGELOG.rst`` with the new
version, followed by release's date (e.g. *13.2.0 - 2018-10-23*).

.. note::

    Use `Semantic versioning`_.

Commit changes to git::

    git commit -a -m "Prepare release <new-version>"

Push changes to your fork and open a pull request::

    git push --set-upstream <fork-name> release-<new-version>

Wait for the tests to pass and the pull request to be approved. Merge the code
to master::

    git checkout master
    git merge --ff-only release-<new-version>

Tag the new release from the latest commit::

    git checkout master
    git tag -m "Version <new-version>" <new-version>

.. note::

    Project's version will be automatically inferred from the git tag using
    `setuptools_scm`_.

Push the tag to the main Resolwe Runtime Utilities git repository::

    git push <upstream-name> master <new-version>

The tagged code will we be released to PyPI automatically. Inspect Travis logs
of the Release step if errors occur.

Preparing pre-release
---------------------

When preparing a pre-release (i.e. an alpha release), one can skip the
"release" commit that updates the change log and just tag the desired commit
with a pre-release tag (e.g. *13.3.0a1*). By pushing it to GitHub, the tagged
code will be automatically tested by Travis CI and then released to PyPI.

.. _Semantic versioning: https://packaging.python.org/en/latest/distributing/#semantic-versioning-preferred
.. _setuptools_scm: https://github.com/pypa/setuptools_scm/
