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

from resolwe_runtime_utils import (
        save, save_list, save_file, save_file_list, error, warning, info, progress, checkrc
    )


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
        self.assertEqual(
            save_list('urls', 'https://www.google.com', 'https://www.genialis.com'),
            '{"urls": ["https://www.google.com", "https://www.genialis.com"]}'
        )


class TestGenSaveFile(ResolweRuntimeUtilsTestCase):

    def test_file(self):
        self.assertEqual(save_file('etc', 'foo.py'),
                         '{"etc": {"file": "foo.py"}}')
        self.assertEqual(save_file('etc', 'foo bar.py'),
                         '{"etc": {"file": "foo bar.py"}}')

    def test_file_with_refs(self):
        self.assertJSONEqual(
            save_file('etc', 'foo.py', 'ref1.txt', 'ref2.txt'),
            '{"etc": {"file": "foo.py", "refs": ["ref1.txt", "ref2.txt"]}}'
        )

    def test_improper_input(self):
        self.assertRaises(TypeError, save_file, 'etc')


class TestGenSaveFileList(ResolweRuntimeUtilsTestCase):

    def test_files(self):
        self.assertEqual(
            save_file_list('src', 'foo.py', 'bar 2.py', 'baz/3.py'),
            '{"src": [{"file": "foo.py"}, {"file": "bar 2.py"}, {"file": "baz/3.py"}]}')

    def test_files_with_refs(self):
        self.assertJSONEqual(
            save_file_list('src', 'foo.py:ref1.gz,ref2.gz', 'bar.py'),
            '{"src": [{"file": "foo.py", "refs": ["ref1.gz", "ref2.gz"]}, {"file": "bar.py"}]}')


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
        self.assertEqual(progress(0), '{"proc.progress": 0}')
        self.assertEqual(progress(1), '{"proc.progress": 1}')

    def test_string(self):
        self.assertEqual(progress('0.1'), '{"proc.progress": 0.1}')

    def test_improper_input(self):
        self.assertRaises(ValueError, progress, 'one')
        self.assertRaises(ValueError, progress, -1)
        self.assertRaises(ValueError, progress, 1.1)


class TestGenCheckRC(ResolweRuntimeUtilsTestCase):

    def test_valid_integers(self):
        self.assertEqual(checkrc(0), '{"proc.rc": 0}')
        self.assertEqual(checkrc(2, 2, "Error"), '{"proc.rc": 0}')
        self.assertJSONEqual(checkrc(1, 2, "Error"), '{"proc.rc": 1, "proc.error": "Error"}')
        self.assertEqual(checkrc(2, 2), '{"proc.rc": 0}')
        self.assertEqual(checkrc(1, 2), '{"proc.rc": 1}')

    def test_valid_strings(self):
        self.assertEqual(checkrc('0'), '{"proc.rc": 0}')
        self.assertEqual(checkrc('2', '2', "Error"), '{"proc.rc": 0}')
        self.assertJSONEqual(checkrc('1', '2', "Error"), '{"proc.rc": 1, "proc.error": "Error"}')
