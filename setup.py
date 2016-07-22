# Copyright 2015 The resolwe-runtime-utils authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Runtime utilities for Resolwe dataflow engine.

See:
https://github.com/genialis/resolwe-runtime-utils
https://github.com/genialis/resolwe
"""

from setuptools import setup, find_packages
# Use codecs' open for a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# Get package metadata from '__about__.py' file
about = {}
with open(path.join(here, '__about__.py'), encoding='utf-8') as f:
    exec(f.read(), about)

setup(
    name=about['__name__'],

    version=about['__version__'],

    description=about['__summary__'],
    long_description=long_description,

    url=about['__url__'],

    author=about['__author__'],
    author_email=about['__email__'],

    license=about['__license__'],

    classifiers=[
        'Development Status :: 4 - Beta',

        'Environment :: Console',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities',

        'License :: OSI Approved :: Apache Software License',

        'Operating System :: OS Independent',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='resolwe runtime utilities library',

    py_modules=['resolwe_runtime_utils'],

    extras_require={
        'dev': ['tox'],
        'docs': ['Sphinx', 'sphinx_rtd_theme'],
        'package': ['twine', 'wheel'],
        'test': ['check-manifest', 'readme', 'pytest-cov'],
    },

    entry_points={
        'console_scripts': [
            're-save = resolwe_runtime_utils:_re_save_main',
            're-export = resolwe_runtime_utils:_re_export_main',
            're-save-list = resolwe_runtime_utils:_re_save_list_main',
            're-save-file = resolwe_runtime_utils:_re_save_file_main',
            're-save-file-list = resolwe_runtime_utils:_re_save_file_list_main',
            're-save-dir = resolwe_runtime_utils:_re_save_dir_main',
            're-save-dir-list = resolwe_runtime_utils:_re_save_dir_list_main',
            're-warning = resolwe_runtime_utils:_re_warning_main',
            're-error = resolwe_runtime_utils:_re_error_main',
            're-info = resolwe_runtime_utils:_re_info_main',
            're-progress = resolwe_runtime_utils:_re_progress_main',
            '_re-checkrc = resolwe_runtime_utils:_re_checkrc_main',
        ],
    },

    test_suite="test_resolwe_runtime_utils",
)
