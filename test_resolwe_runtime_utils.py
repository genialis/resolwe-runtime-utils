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

# pylint: disable=missing-docstring
from io import StringIO
import json
import os
import shutil
import sys
from unittest import TestCase
from unittest.mock import patch

import responses
import requests

from resolwe_runtime_utils import (
    annotate_entity,
    save,
    export_file,
    import_file,
    ImportedFormat,
    save_list,
    save_file,
    save_file_list,
    save_dir,
    save_dir_list,
    info,
    warning,
    error,
    progress,
    checkrc,
    _re_annotate_entity_main,
    _re_save_main,
    _re_export_main,
    _re_save_list_main,
    _re_save_file_main,
    _re_save_file_list_main,
    _re_save_dir_main,
    _re_save_dir_list_main,
    _re_info_main,
    _re_warning_main,
    _re_error_main,
    _re_progress_main,
    _re_checkrc_main,
)


TEST_ROOT = os.path.abspath(os.path.dirname(__file__))


class ResolweRuntimeUtilsTestCase(TestCase):
    def assertJSONEqual(self, json_, expected_json):  # pylint: disable=invalid-name
        self.assertEqual(json.loads(json_), json.loads(expected_json))


class TestAnnotate(ResolweRuntimeUtilsTestCase):
    def test_annotation(self):
        self.assertEqual(annotate_entity('foo', '0'), '{"_entity.descriptor.foo": 0}')


class TestSave(ResolweRuntimeUtilsTestCase):
    def test_number(self):
        self.assertEqual(save('foo', '0'), '{"foo": 0}')

    def test_quote(self):
        self.assertEqual(save('foo', '"'), '{"foo": "\\""}')

    def test_string(self):
        self.assertEqual(save('bar', 'baz'), '{"bar": "baz"}')
        self.assertEqual(
            save('proc.warning', 'Warning foo'), '{"proc.warning": "Warning foo"}'
        )
        self.assertEqual(save('number', '"0"'), '{"number": "0"}')

    def test_hash(self):
        self.assertEqual(
            save('etc', '{"file": "foo.py"}'), '{"etc": {"file": "foo.py"}}'
        )

    def test_improper_input(self):
        self.assertRaises(TypeError, save, 'proc.rc')
        self.assertRaises(TypeError, save, 'proc.rc', '0', 'Foo')
        # NOTE: If a user doesn't put a JSON hash in single-quotes (''), then
        # Bash will split it into multiple arguments as shown with the test
        # case below.
        self.assertRaises(TypeError, save, 'etc', '{file:', 'foo.py}')


class TestExport(ResolweRuntimeUtilsTestCase):
    @patch('os.path.isfile', return_value=True)
    def test_filename(self, isfile_mock):
        self.assertEqual(export_file('foo.txt'), 'export foo.txt')

    @patch('os.path.isfile', return_value=False)
    def test_missing_file(self, isfile_mock):
        self.assertEqual(
            export_file('foo.txt'),
            '{"proc.error": "Referenced file does not exist: \'foo.txt\'."}',
        )

    def test_many_filenames(self):
        self.assertRaises(TypeError, export_file, 'etc', 'foo.txt', 'bar.txt')


class TestSaveList(ResolweRuntimeUtilsTestCase):
    def test_paths(self):
        self.assertEqual(
            save_list('src', 'file1.txt', 'file 2.txt'),
            '{"src": ["file1.txt", "file 2.txt"]}',
        )

    def test_urls(self):
        self.assertJSONEqual(
            save_list(
                'urls',
                '{"name": "View", "url": "https://www.google.com"}',
                '{"name": "View", "url": "https://www.genialis.com"}',
            ),
            '{"urls": [{"url": "https://www.google.com", "name": "View"}, '
            '{"url": "https://www.genialis.com", "name": "View"}]}',
        )


class TestSaveFile(ResolweRuntimeUtilsTestCase):
    @patch('os.path.isfile', return_value=True)
    def test_file(self, isfile_mock):
        self.assertEqual(save_file('etc', 'foo.py'), '{"etc": {"file": "foo.py"}}')
        self.assertEqual(
            save_file('etc', 'foo bar.py'), '{"etc": {"file": "foo bar.py"}}'
        )

    @patch('os.path.isfile', return_value=True)
    def test_file_with_refs(self, isfile_mock):
        self.assertJSONEqual(
            save_file('etc', 'foo.py', 'ref1.txt', 'ref2.txt'),
            '{"etc": {"file": "foo.py", "refs": ["ref1.txt", "ref2.txt"]}}',
        )

    def test_missing_file(self):
        self.assertEqual(
            save_file('etc', 'foo.py'),
            '{"proc.error": "Output \'etc\' set to a missing file: \'foo.py\'."}',
        )
        self.assertEqual(
            save_file('etc', 'foo bar.py'),
            '{"proc.error": "Output \'etc\' set to a missing file: \'foo bar.py\'."}',
        )

    @patch('os.path.isfile', side_effect=[True, False, False])
    def test_file_with_missing_refs(self, isfile_mock):
        self.assertEqual(
            save_file('src', 'foo.py', 'ref1.gz', 'ref2.gz'),
            '{"proc.error": "Output \'src\' set to missing references: \'ref1.gz, ref2.gz\'."}',
        )

    def test_improper_input(self):
        self.assertRaises(TypeError, save_file, 'etc')


class TestSaveFileList(ResolweRuntimeUtilsTestCase):
    @patch('os.path.isfile', return_value=True)
    def test_files(self, isfile_mock):
        self.assertEqual(
            save_file_list('src', 'foo.py', 'bar 2.py', 'baz/3.py'),
            '{"src": [{"file": "foo.py"}, {"file": "bar 2.py"}, {"file": "baz/3.py"}]}',
        )

    @patch('os.path.isfile', return_value=True)
    def test_file_with_refs(self, isfile_mock):
        self.assertJSONEqual(
            save_file_list('src', 'foo.py:ref1.gz,ref2.gz', 'bar.py'),
            '{"src": [{"file": "foo.py", "refs": ["ref1.gz", "ref2.gz"]}, {"file": "bar.py"}]}',
        )

    def test_missing_file(self):
        self.assertEqual(
            save_file_list('src', 'foo.py', 'bar 2.py', 'baz/3.py'),
            '{"proc.error": "Output \'src\' set to a missing file: \'foo.py\'."}',
        )

    def test_missing_file_with_refs(self):
        self.assertEqual(
            save_file_list('src', 'foo.py:ref1.gz,ref2.gz', 'bar.py'),
            '{"proc.error": "Output \'src\' set to a missing file: \'foo.py\'."}',
        )

    @patch('os.path.isfile', side_effect=[True, False, False])
    def test_file_with_missing_refs(self, isfile_mock):
        self.assertEqual(
            save_file_list('src', 'foo.py:ref1.gz,ref2.gz'),
            '{"proc.error": "Output \'src\' set to missing references: \'ref1.gz, ref2.gz\'."}',
        )

    def test_files_invalid_format(self):
        self.assertEqual(
            save_file_list('src', 'foo.py:ref1.gz:ref2.gz', 'bar.py'),
            '{"proc.error": "Only one colon \':\' allowed in file-refs specification."}',
        )


class TestSaveDir(ResolweRuntimeUtilsTestCase):
    @patch('os.path.isdir', return_value=True)
    def test_dir(self, isdir_mock):
        self.assertEqual(save_dir('etc', 'foo'), '{"etc": {"dir": "foo"}}')
        self.assertEqual(save_dir('etc', 'foo bar'), '{"etc": {"dir": "foo bar"}}')

    @patch('os.path.isdir', return_value=True)
    def test_dir_with_refs(self, isdir_mock):
        self.assertJSONEqual(
            save_dir('etc', 'foo', 'ref1.txt', 'ref2.txt'),
            '{"etc": {"dir": "foo", "refs": ["ref1.txt", "ref2.txt"]}}',
        )

    def test_missing_dir(self):
        self.assertEqual(
            save_dir('etc', 'foo'),
            '{"proc.error": "Output \'etc\' set to a missing directory: \'foo\'."}',
        )
        self.assertEqual(
            save_dir('etc', 'foo bar'),
            '{"proc.error": "Output \'etc\' set to a missing directory: \'foo bar\'."}',
        )

    @patch('os.path.isdir', side_effect=[True, False, False])
    def test_dir_with_missing_refs(self, isdir_mock):
        self.assertEqual(
            save_dir('etc', 'foo', 'ref1.gz', 'ref2.gz'),
            '{"proc.error": "Output \'etc\' set to missing references: \'ref1.gz, ref2.gz\'."}',
        )

    def test_improper_input(self):
        self.assertRaises(TypeError, save_dir, 'etc')


class TestSaveDirList(ResolweRuntimeUtilsTestCase):
    @patch('os.path.isdir', return_value=True)
    def test_dirs(self, isdir_mock):
        self.assertEqual(
            save_dir_list('src', 'dir1', 'dir 2', 'dir/3'),
            '{"src": [{"dir": "dir1"}, {"dir": "dir 2"}, {"dir": "dir/3"}]}',
        )

    @patch('os.path.isdir', return_value=True)
    def test_dir_with_refs(self, isfile_mock):
        self.assertJSONEqual(
            save_dir_list('src', 'dir1:ref1.gz,ref2.gz', 'dir2'),
            '{"src": [{"dir": "dir1", "refs": ["ref1.gz", "ref2.gz"]}, {"dir": "dir2"}]}',
        )

    def test_missing_dir(self):
        self.assertEqual(
            save_dir_list('src', 'dir1', 'dir 2', 'dir/3'),
            '{"proc.error": "Output \'src\' set to a missing directory: \'dir1\'."}',
        )

    @patch('os.path.isdir', side_effect=[True, False, False])
    def test_dir_with_missing_refs(self, isdir_mock):
        self.assertEqual(
            save_dir_list('src', 'dir:ref1.gz,ref2.gz'),
            '{"proc.error": "Output \'src\' set to missing references: \'ref1.gz, ref2.gz\'."}',
        )

    def test_files_invalid_format(self):
        self.assertEqual(
            save_dir_list('src', 'dir1:ref1.bar:ref2.bar', 'dir2'),
            '{"proc.error": "Only one colon \':\' allowed in dir-refs specification."}',
        )


class TestInfo(ResolweRuntimeUtilsTestCase):
    def test_string(self):
        self.assertEqual(info('Some info'), '{"proc.info": "Some info"}')

    def test_improper_input(self):
        self.assertRaises(TypeError, info, 'First', 'Second')


class TestWarning(ResolweRuntimeUtilsTestCase):
    def test_string(self):
        self.assertEqual(warning('Some warning'), '{"proc.warning": "Some warning"}')

    def test_improper_input(self):
        self.assertRaises(TypeError, warning, 'First', 'Second')


class TestError(ResolweRuntimeUtilsTestCase):
    def test_string(self):
        self.assertEqual(error('Some error'), '{"proc.error": "Some error"}')

    def test_improper_input(self):
        self.assertRaises(TypeError, error, 'First', 'Second')


class TestProgress(ResolweRuntimeUtilsTestCase):
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
        self.assertEqual(
            progress(None), '{"proc.warning": "Progress must be a float."}'
        )
        self.assertEqual(
            progress('one'), '{"proc.warning": "Progress must be a float."}'
        )
        self.assertEqual(
            progress('[0.1]'), '{"proc.warning": "Progress must be a float."}'
        )
        self.assertEqual(
            progress(-1),
            '{"proc.warning": "Progress must be a float between 0 and 1."}',
        )
        self.assertEqual(
            progress(1.1),
            '{"proc.warning": "Progress must be a float between 0 and 1."}',
        )
        self.assertEqual(
            progress('1.1'),
            '{"proc.warning": "Progress must be a float between 0 and 1."}',
        )


class TestCheckRC(ResolweRuntimeUtilsTestCase):
    def test_valid_integers(self):
        self.assertEqual(checkrc(0), '{"proc.rc": 0}')
        self.assertEqual(checkrc(2, 2, 'Error'), '{"proc.rc": 0}')
        self.assertJSONEqual(
            checkrc(1, 2, 'Error'), '{"proc.rc": 1, "proc.error": "Error"}'
        )
        self.assertEqual(checkrc(2, 2), '{"proc.rc": 0}')
        self.assertEqual(checkrc(1, 2), '{"proc.rc": 1}')

    def test_valid_strings(self):
        self.assertEqual(checkrc('0'), '{"proc.rc": 0}')
        self.assertEqual(checkrc('2', '2', 'Error'), '{"proc.rc": 0}')
        self.assertJSONEqual(
            checkrc('1', '2', 'Error'), '{"proc.rc": 1, "proc.error": "Error"}'
        )

    def test_error_message_not_string(self):
        self.assertJSONEqual(
            checkrc(1, ['Error']), '{"proc.rc": 1, "proc.error": ["Error"]}'
        )

    def test_improper_input(self):
        self.assertEqual(
            checkrc(None), '{"proc.error": "Invalid return code: \'None\'."}'
        )
        self.assertEqual(
            checkrc('foo'), '{"proc.error": "Invalid return code: \'foo\'."}'
        )
        self.assertEqual(
            checkrc(1, 'foo', 'Error'),
            '{"proc.error": "Invalid return code: \'foo\'."}',
        )
        self.assertEqual(
            checkrc(1, None, 'Error'),
            '{"proc.error": "Invalid return code: \'None\'."}',
        )


class ImportFileTestCase(TestCase):

    _test_data_dir = os.path.join(TEST_ROOT, '.test_data')

    def setUp(self):
        # Clean after terminated tests
        shutil.rmtree(self._test_data_dir, ignore_errors=True)

        os.mkdir(self._test_data_dir)
        os.chdir(self._test_data_dir)

    def tearDown(self):
        os.chdir(TEST_ROOT)
        shutil.rmtree(self._test_data_dir)

    def _file(self, path):
        """Add path prefix to test file."""
        return os.path.join(TEST_ROOT, 'test_files', path)

    def assertImportFile(self, src, dst, returned_name):
        # Test both
        src = self._file(src)
        file_name = import_file(src, dst)
        assert file_name == returned_name
        assert os.path.exists(returned_name), "file not found"
        assert os.path.exists(returned_name + '.gz'), "file not found"
        os.remove(returned_name)
        os.remove(returned_name + '.gz')

        # Test extracted
        file_name = import_file(src, dst, ImportedFormat.EXTRACTED)
        assert file_name == returned_name
        assert os.path.exists(returned_name), "file not found"
        assert not os.path.exists(returned_name + '.gz'), "file should not exist"
        os.remove(returned_name)

        # Test compressed
        file_name = import_file(src, dst, ImportedFormat.COMPRESSED)
        assert file_name == returned_name + '.gz'
        assert os.path.exists(returned_name + '.gz'), "file not found"
        assert not os.path.exists(returned_name), "file should not exist"
        os.remove(returned_name + '.gz')

    def test_uncompressed(self):
        self.assertImportFile(
            'some file.1.txt', 'test uncompressed.txt', 'test uncompressed.txt'
        )

    def test_gz(self):
        self.assertImportFile('some file.1.txt.gz', 'test gz.txt.gz', 'test gz.txt')

    def test_7z(self):
        self.assertImportFile('some file.1.txt.zip', 'test 7z.txt.zip', 'test 7z.txt')

        file_name = import_file(self._file('some folder.tar.gz'), 'some folder.tar.gz')
        assert file_name == 'some folder'
        assert os.path.isdir('some folder'), "directory not found"
        assert os.path.exists('some folder.tar.gz'), "file not found"
        shutil.rmtree('some folder')
        os.remove('some folder.tar.gz')

        file_name = import_file(
            self._file('some folder.tar.gz'),
            'some folder.tar.gz',
            ImportedFormat.COMPRESSED,
        )
        assert file_name == 'some folder.tar.gz'
        assert not os.path.isdir('some folder'), "directory should not exist"
        assert os.path.exists('some folder.tar.gz'), "file not found"

        file_name = import_file(self._file('some folder 1.zip'), 'some folder 1.zip')
        assert file_name == 'some folder 1'
        assert os.path.isdir('some folder 1'), "directory not found"
        assert os.path.exists('some folder 1.tar.gz'), "file not found"
        shutil.rmtree('some folder 1')
        os.remove('some folder 1.tar.gz')

        file_name = import_file(
            self._file('some folder 1.zip'),
            'some folder 1.zip',
            ImportedFormat.COMPRESSED,
        )
        assert file_name == 'some folder 1.tar.gz'
        assert not os.path.isdir('some folder 1'), "directory should not exist"
        assert os.path.exists('some folder 1.tar.gz'), "file not found"

    def test_7z_corrupted(self):
        with self.assertRaises(ValueError, msg='failed to extract file: corrupted.zip'):
            import_file(self._file('corrupted.zip'), 'corrupted.zip')

    def test_gz_corrupted(self):
        with self.assertRaises(
            ValueError, msg='invalid gzip file format: corrupted.gz'
        ):
            import_file(self._file('corrupted.gz'), 'corrupted.gz')

        with self.assertRaises(
            ValueError, msg='invalid gzip file format: corrupted.gz'
        ):
            import_file(
                self._file('corrupted.gz'), 'corrupted.gz', ImportedFormat.COMPRESSED
            )

    @responses.activate
    def test_uncompressed_url(self):
        responses.add(
            responses.GET, 'https://testurl/someslug', status=200, body='some text'
        )

        import_file('https://testurl/someslug', 'test uncompressed.txt')
        assert os.path.exists('test uncompressed.txt'), "file not found"
        assert os.path.exists('test uncompressed.txt.gz'), "file not found"

    @responses.activate
    def test_gz_url(self):
        # Return gzipped file
        responses.add(
            responses.GET,
            'https://testurl/someslug',
            status=200,
            body=bytes.fromhex(
                '1f8b0808a6cea15c0003736f6d652066696c652e312e747874002bcecf4d'
                '552849ad28e10200bce62c190a000000'
            ),
        )

        import_file('https://testurl/someslug', 'test uncompressed.txt.gz')
        assert os.path.exists('test uncompressed.txt'), "file not found"
        assert os.path.exists('test uncompressed.txt.gz'), "file not found"

    @responses.activate
    def test_7z_url(self):
        # Return zipped file
        responses.add(
            responses.GET,
            'http://testurl/someslug',
            status=200,
            body=bytes.fromhex(
                '504b03041400080008000c5b814e0000000000000000000000000f001000'
                '736f6d652066696c652e312e74787455580c009fdaa15cc7d8a15cf50114'
                '002bcecf4d552849ad28e10200504b0708bce62c190c0000000a00000050'
                '4b010215031400080008000c5b814ebce62c190c0000000a0000000f000c'
                '000000000000000040a48100000000736f6d652066696c652e312e747874'
                '555808009fdaa15cc7d8a15c504b05060000000001000100490000005900'
                '00000000'
            ),
        )

        import_file('http://testurl/someslug', 'test uncompressed.txt.zip')
        assert os.path.exists('test uncompressed.txt'), "file not found"
        assert os.path.exists('test uncompressed.txt.gz'), "file not found"

    def test_invalid_url(self):
        with self.assertRaises(requests.exceptions.ConnectionError):
            import_file('http://testurl/someslug', 'test uncompressed.txt.zip')


class TestConsoleCommands(ResolweRuntimeUtilsTestCase):
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_annotate(self, stdout_mock):
        with patch.object(sys, 'argv', ['_', 'foo.bar', '2']):
            _re_annotate_entity_main()
            self.assertEqual(
                stdout_mock.getvalue(), '{"_entity.descriptor.foo.bar": 2}\n'
            )

    @patch('sys.stdout', new_callable=StringIO)
    def test_error_handling(self, stdout_mock):
        with patch.object(sys, 'argv', ['re-save', 'test', '123', 'test', '345']):
            _re_save_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                '{"proc.error": "Unexpected error in \'re-save\': save() takes 2 positional arguments but 4 were given"}\n',
            )

    @patch('sys.stdout', new_callable=StringIO)
    def test_re_save(self, stdout_mock):
        with patch.object(sys, 'argv', ['_', 'foo.bar', '2']):
            _re_save_main()
            self.assertEqual(stdout_mock.getvalue(), '{"foo.bar": 2}\n')

    @patch('os.path.isfile', return_value=True)
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_export(self, stdout_mock, isfile_mock):
        with patch.object(sys, 'argv', ['_', 'foo.bar']):
            _re_export_main()
            self.assertEqual(stdout_mock.getvalue(), 'export foo.bar\n')

    @patch('sys.stdout', new_callable=StringIO)
    def test_re_save_list(self, stdout_mock):
        with patch.object(sys, 'argv', ['_', 'foo.bar', '2', 'baz']):
            _re_save_list_main()
            self.assertEqual(stdout_mock.getvalue(), '{"foo.bar": [2, "baz"]}\n')

    @patch('os.path.isfile', return_value=True)
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_save_file(self, stdout_mock, isfile_mock):
        with patch.object(sys, 'argv', ['_', 'foo.bar', 'baz.py']):
            _re_save_file_main()
            self.assertEqual(
                stdout_mock.getvalue(), '{"foo.bar": {"file": "baz.py"}}\n'
            )

    @patch('os.path.isfile', return_value=True)
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_save_file_list(self, stdout_mock, isfile_mock):
        with patch.object(sys, 'argv', ['_', 'foo.bar', 'baz.py', 'baz 2.py']):
            _re_save_file_list_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                '{"foo.bar": [{"file": "baz.py"}, {"file": "baz 2.py"}]}\n',
            )

    @patch('os.path.isdir', return_value=True)
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_save_dir(self, stdout_mock, isdir_mock):
        with patch.object(sys, 'argv', ['_', 'foo.bar', 'baz']):
            _re_save_dir_main()
            self.assertEqual(stdout_mock.getvalue(), '{"foo.bar": {"dir": "baz"}}\n')

    @patch('os.path.isdir', return_value=True)
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_save_dir_list(self, stdout_mock, isfile_mock):
        with patch.object(sys, 'argv', ['_', 'foo.bar', 'baz', 'baz 2']):
            _re_save_dir_list_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                '{"foo.bar": [{"dir": "baz"}, {"dir": "baz 2"}]}\n',
            )

    @patch('sys.stdout', new_callable=StringIO)
    def test_re_info(self, stdout_mock):
        with patch.object(sys, 'argv', ['_', 'some info']):
            _re_info_main()
            self.assertEqual(stdout_mock.getvalue(), '{"proc.info": "some info"}\n')

    @patch('sys.stdout', new_callable=StringIO)
    def test_re_warning(self, stdout_mock):
        with patch.object(sys, 'argv', ['_', 'some warning']):
            _re_warning_main()
            self.assertEqual(
                stdout_mock.getvalue(), '{"proc.warning": "some warning"}\n'
            )

    @patch('sys.stdout', new_callable=StringIO)
    def test_re_error(self, stdout_mock):
        with patch.object(sys, 'argv', ['_', 'some error']):
            _re_error_main()
            self.assertEqual(stdout_mock.getvalue(), '{"proc.error": "some error"}\n')

    @patch('sys.stdout', new_callable=StringIO)
    def test_re_progress(self, stdout_mock):
        with patch.object(sys, 'argv', ['_', '0.7']):
            _re_progress_main()
            self.assertEqual(stdout_mock.getvalue(), '{"proc.progress": 0.7}\n')

    @patch('sys.stdout', new_callable=StringIO)
    def test_re_checkrc(self, stdout_mock):
        with patch.object(sys, 'argv', ['_', '1', '2', 'error']):
            _re_checkrc_main()
            self.assertJSONEqual(
                stdout_mock.getvalue(), '{"proc.rc": 1, "proc.error": "error"}\n'
            )
