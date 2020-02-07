# Copyright 2019 Genialis, Inc.
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

import os.path
import setuptools

base_dir = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
with open(os.path.join(base_dir, 'README.rst')) as fh:
    long_description = fh.read()

# Get package metadata from '__about__.py' file
about = {}
with open(os.path.join(base_dir, '__about__.py')) as fh:
    exec(fh.read(), about)

setuptools.setup(
    name=about['__name__'],
    use_scm_version=True,
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    keywords='resolwe runtime utilities library',
    py_modules=['resolwe_runtime_utils'],
    install_requires=['requests>=2.20.1'],
    extras_require={
        'dev': ['tox'],
        'docs': ['Sphinx', 'sphinx_rtd_theme'],
        'package': ['twine', 'wheel'],
        'test': [
            'black',
            'check-manifest',
            'readme',
            'pytest-cov',
            'responses',
            'setuptools_scm',
        ],
    },
    entry_points={
        'console_scripts': [
            're-annotate-entity = resolwe_runtime_utils:_re_annotate_entity_main',
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
        ]
    },
    test_suite="test_resolwe_runtime_utils",
)
