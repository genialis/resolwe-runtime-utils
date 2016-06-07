##########
Change Log
##########

All notable changes to the |project_name| project will be documented in this
file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.


==========
Unreleased
==========

Added
-----
- Use Travis CI to run the tests
- Add test coverage and track it with Codecov
- Start writing the Change Log and include it in the Documentation
- Add ``docs`` and ``packaging`` Tox testing environments
- Add ``dev``, a list of extra requirements for development
- Add ``save_list`` and ``save_file_list`` functions and console commands

Changed
-------
- Consistently use *Resolwe Runtime Utilities* as the project name/title
- Improve documentation
- Use py.test as the test runner since its pytest-cov plugin enables to easily
  compute the test coverage while running the tests
