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

# pylint: disable=missing-docstring
import json
from unittest import TestCase
from unittest.mock import patch

from resolwe_runtime_utils import (
    save, save_list, save_file, save_dir, save_file_list,
    save_dir_list, error, warning, info, progress, checkrc)


class ResolweRuntimeUtilsTestCase(TestCase):
    def assertJSONEqual(self, json_, expected_json):  # pylint: disable=invalid-name
        self.assertEqual(json.loads(json_), json.loads(expected_json))


class TestGenSave(ResolweRuntimeUtilsTestCase):

    def test_number(self):
        self.assertEqual(save('foo', '0'), '{"foo": 0}')

    def test_string(self):
        self.assertEqual(save('bar', 'baz'), '{"bar": "baz"}')
        self.assertEqual(save('proc.warning', 'Warning foo'),
                         '{"proc.warning": "Warning foo"}')
        self.assertEqual(save('number', '"0"'), '{"number": "0"}')

    def test_hash(self):
        self.assertEqual(save('etc', '{"file": "foo.py"}'),
                         '{"etc": {"file": "foo.py"}}')

    def test_improper_input(self):
        self.assertRaises(TypeError, save, 'proc.rc')
        self.assertRaises(TypeError, save, 'proc.rc', '0', 'Foo')
        # NOTE: If a user doesn't put a JSON hash in single-quotes (''), then
        # Bash will split it into multiple arguments as shown with the test
        # case below.
        self.assertRaises(TypeError, save, 'etc', '{file:', 'foo.py}')


class TestGenSaveList(ResolweRuntimeUtilsTestCase):

    def test_paths(self):
        self.assertEqual(save_list('src', 'file1.txt', 'file 2.txt'),
                         '{"src": ["file1.txt", "file 2.txt"]}')

    def test_urls(self):
        self.assertJSONEqual(
            save_list('urls', '{"name": "View", "url": "https://www.google.com"}',
                      '{"name": "View", "url": "https://www.genialis.com"}'),
            '{"urls": [{"url": "https://www.google.com", "name": "View"}, '
            '{"url": "https://www.genialis.com", "name": "View"}]}'
        )


class TestGenSaveFile(ResolweRuntimeUtilsTestCase):

    @patch('os.path.isfile', return_value=True)
    def test_file(self, isfile_mock):
        self.assertEqual(save_file('etc', 'foo.py'), '{"etc": {"file": "foo.py"}}')
        self.assertEqual(save_file('etc', 'foo bar.py'), '{"etc": {"file": "foo bar.py"}}')

    @patch('os.path.isfile', return_value=True)
    def test_file_with_refs(self, isfile_mock):
        self.assertJSONEqual(save_file('etc', 'foo.py', 'ref1.txt', 'ref2.txt'),
                             '{"etc": {"file": "foo.py", "refs": ["ref1.txt", "ref2.txt"]}}')

    def test_missing_file(self):
        self.assertEqual(save_file('etc', 'foo.py'),
                         '{"proc.error": "Output \'etc\' set to a missing file: \'foo.py\'."}')
        self.assertEqual(save_file('etc', 'foo bar.py'),
                         '{"proc.error": "Output \'etc\' set to a missing file: \'foo bar.py\'."}')

    @patch('os.path.isfile', side_effect=[True, False, False])
    def test_file_with_missing_refs(self, isfile_mock):
        self.assertEqual(
            save_file('src', 'foo.py', 'ref1.gz', 'ref2.gz'),
            '{"proc.error": "Output \'src\' set to missing references: \'ref1.gz, ref2.gz\'."}'
        )

    def test_improper_input(self):
        self.assertRaises(TypeError, save_file, 'etc')


class TestGenSaveFileList(ResolweRuntimeUtilsTestCase):

    @patch('os.path.isfile', return_value=True)
    def test_files(self, isfile_mock):
        self.assertEqual(
            save_file_list('src', 'foo.py', 'bar 2.py', 'baz/3.py'),
            '{"src": [{"file": "foo.py"}, {"file": "bar 2.py"}, {"file": "baz/3.py"}]}'
        )

    @patch('os.path.isfile', return_value=True)
    def test_file_with_refs(self, isfile_mock):
        self.assertJSONEqual(
            save_file_list('src', 'foo.py:ref1.gz,ref2.gz', 'bar.py'),
            '{"src": [{"file": "foo.py", "refs": ["ref1.gz", "ref2.gz"]}, {"file": "bar.py"}]}'
        )

    def test_missing_file(self):
        self.assertEqual(save_file_list('src', 'foo.py', 'bar 2.py', 'baz/3.py'),
                         '{"proc.error": "Output \'src\' set to a missing file: \'foo.py\'."}')

    def test_missing_file_with_refs(self):
        self.assertEqual(save_file_list('src', 'foo.py:ref1.gz,ref2.gz', 'bar.py'),
                         '{"proc.error": "Output \'src\' set to a missing file: \'foo.py\'."}')

    @patch('os.path.isfile', side_effect=[True, False, False])
    def test_file_with_missing_refs(self, isfile_mock):
        self.assertEqual(
            save_file_list('src', 'foo.py:ref1.gz,ref2.gz'),
            '{"proc.error": "Output \'src\' set to missing references: \'ref1.gz, ref2.gz\'."}'
        )

    def test_files_invalid_format(self):
        self.assertEqual(
            save_file_list('src', 'foo.py:ref1.gz:ref2.gz', 'bar.py'),
            '{"proc.error": "Only one colon \':\' allowed in file-refs specification."}'
        )


class TestGenSaveDir(ResolweRuntimeUtilsTestCase):

    @patch('os.path.isdir', return_value=True)
    def test_dir(self, isdir_mock):
        self.assertEqual(save_dir('etc', 'foo'), '{"etc": {"dir": "foo"}}')
        self.assertEqual(save_dir('etc', 'foo bar'), '{"etc": {"dir": "foo bar"}}')

    @patch('os.path.isdir', return_value=True)
    def test_dir_with_refs(self, isdir_mock):
        self.assertJSONEqual(save_dir('etc', 'foo', 'ref1.txt', 'ref2.txt'),
                             '{"etc": {"dir": "foo", "refs": ["ref1.txt", "ref2.txt"]}}')

    def test_missing_dir(self):
        self.assertEqual(save_dir('etc', 'foo'),
                         '{"proc.error": "Output \'etc\' set to a missing directory: \'foo\'."}')
        self.assertEqual(
            save_dir('etc', 'foo bar'),
            '{"proc.error": "Output \'etc\' set to a missing directory: \'foo bar\'."}'
        )

    @patch('os.path.isdir', side_effect=[True, False, False])
    def test_dir_with_missing_refs(self, isdir_mock):
        self.assertEqual(
            save_dir('etc', 'foo', 'ref1.gz', 'ref2.gz'),
            '{"proc.error": "Output \'etc\' set to missing references: \'ref1.gz, ref2.gz\'."}'
        )

    def test_improper_input(self):
        self.assertRaises(TypeError, save_dir, 'etc')


class TestGenSaveDirList(ResolweRuntimeUtilsTestCase):

    @patch('os.path.isdir', return_value=True)
    def test_dirs(self, isdir_mock):
        self.assertEqual(save_dir_list('src', 'dir1', 'dir 2', 'dir/3'),
                         '{"src": [{"dir": "dir1"}, {"dir": "dir 2"}, {"dir": "dir/3"}]}')

    @patch('os.path.isdir', return_value=True)
    def test_dir_with_refs(self, isfile_mock):
        self.assertJSONEqual(
            save_dir_list('src', 'dir1:ref1.gz,ref2.gz', 'dir2'),
            '{"src": [{"dir": "dir1", "refs": ["ref1.gz", "ref2.gz"]}, {"dir": "dir2"}]}'
        )

    def test_missing_dir(self):
        self.assertEqual(save_dir_list('src', 'dir1', 'dir 2', 'dir/3'),
                         '{"proc.error": "Output \'src\' set to a missing directory: \'dir1\'."}')

    @patch('os.path.isdir', side_effect=[True, False, False])
    def test_dir_with_missing_refs(self, isdir_mock):
        self.assertEqual(
            save_dir_list('src', 'dir:ref1.gz,ref2.gz'),
            '{"proc.error": "Output \'src\' set to missing references: \'ref1.gz, ref2.gz\'."}'
        )

    def test_files_invalid_format(self):
        self.assertEqual(
            save_dir_list('src', 'dir1:ref1.bar:ref2.bar', 'dir2'),
            '{"proc.error": "Only one colon \':\' allowed in dir-refs specification."}'
        )


class TestGenInfo(ResolweRuntimeUtilsTestCase):

    def test_string(self):
        self.assertEqual(info('Some info'), '{"proc.info": "Some info"}')

    def test_improper_input(self):
        self.assertRaises(TypeError, info, 'First', 'Second')


class TestGenWarning(ResolweRuntimeUtilsTestCase):

    def test_string(self):
        self.assertEqual(warning('Some warning'), '{"proc.warning": "Some warning"}')

    def test_improper_input(self):
        self.assertRaises(TypeError, warning, 'First', 'Second')


class TestGenError(ResolweRuntimeUtilsTestCase):

    def test_string(self):
        self.assertEqual(error('Some error'), '{"proc.error": "Some error"}')

    def test_improper_input(self):
        self.assertRaises(TypeError, error, 'First', 'Second')


class TestGenProgress(ResolweRuntimeUtilsTestCase):

    def test_number(self):
        self.assertEqual(progress(0.1), '{"proc.progress": 0.1}')
        self.assertEqual(progress(0), '{"proc.progress": 0.0}')
        self.assertEqual(progress(1), '{"proc.progress": 1.0}')

    def test_string(self):
        self.assertEqual(progress('0.1'), '{"proc.progress": 0.1}')
        self.assertEqual(progress('0'), '{"proc.progress": 0.0}')
        self.assertEqual(progress('1'), '{"proc.progress": 1.0}')

    def test_bool(self):
        self.assertEqual(progress(True), '{"proc.progress": 1.0}')

    def test_improper_input(self):
        self.assertEqual(progress(None), '{"proc.warning": "Progress must be a float."}')
        self.assertEqual(progress('one'), '{"proc.warning": "Progress must be a float."}')
        self.assertEqual(progress('[0.1]'), '{"proc.warning": "Progress must be a float."}')
        self.assertEqual(progress(-1),
                         '{"proc.warning": "Progress must be a float between 0 and 1."}')
        self.assertEqual(progress(1.1),
                         '{"proc.warning": "Progress must be a float between 0 and 1."}')
        self.assertEqual(progress('1.1'),
                         '{"proc.warning": "Progress must be a float between 0 and 1."}')


class TestGenCheckRC(ResolweRuntimeUtilsTestCase):

    def test_valid_integers(self):
        self.assertEqual(checkrc(0), '{"proc.rc": 0}')
        self.assertEqual(checkrc(2, 2, 'Error'), '{"proc.rc": 0}')
        self.assertJSONEqual(checkrc(1, 2, 'Error'), '{"proc.rc": 1, "proc.error": "Error"}')
        self.assertEqual(checkrc(2, 2), '{"proc.rc": 0}')
        self.assertEqual(checkrc(1, 2), '{"proc.rc": 1}')

    def test_valid_strings(self):
        self.assertEqual(checkrc('0'), '{"proc.rc": 0}')
        self.assertEqual(checkrc('2', '2', 'Error'), '{"proc.rc": 0}')
        self.assertJSONEqual(checkrc('1', '2', 'Error'), '{"proc.rc": 1, "proc.error": "Error"}')

    def test_error_message_not_string(self):
        self.assertJSONEqual(checkrc(1, ['Error']),
                '{"proc.rc": 1, "proc.error": ["Error"]}')

    def test_improper_input(self):
        self.assertEqual(checkrc(None), '{"proc.error": "Invalid return code: \'None\'."}')
        self.assertEqual(checkrc('foo'), '{"proc.error": "Invalid return code: \'foo\'."}')
        self.assertEqual(checkrc(1, 'foo', 'Error'),
                         '{"proc.error": "Invalid return code: \'foo\'."}')
        self.assertEqual(checkrc(1, None, 'Error'),
                         '{"proc.error": "Invalid return code: \'None\'."}')
