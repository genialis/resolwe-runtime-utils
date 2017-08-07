##########
Change Log
##########

All notable changes to the |project_name| project will be documented in this
file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

==================
1.2.0 - 2017-08-08
==================

Changed
-------
- Handle unexpected errors in re-* functions and print an error with a
  descriptive message
- Escape double quotes in values of ``re-*`` commands


==================
1.1.0 - 2016-07-25
==================

Added
-----
- Add tests for all console commands (``TestConsoleCommands``)
- Add ``export`` function and console command


==================
1.0.0 - 2016-06-16
==================

Added
-----
- Use Travis CI to run the tests
- Add test coverage and track it with Codecov
- Start writing the Change Log and include it in the Documentation
- Add ``docs`` and ``packaging`` Tox testing environments
- Add ``dev``, a list of extra requirements for development
- Add ``save_list`` and ``save_file_list`` functions and console commands
- Add ``save_dir`` and ``save_dir_list`` functions and console commands

Changed
-------
- Consistently use *Resolwe Runtime Utilities* as the project name/title
- Improve documentation
- Use py.test as the test runner since its pytest-cov plugin enables to easily
  compute the test coverage while running the tests
- Create ``_get_json`` auxiliary function use it in ``save`` and ``save_list``
  functions
- Check if files exist before saving them
- Save Resolwe errors instead of raising Python exceptions
- Make ``checkrc`` and ``progress`` functions more robust to improper input
