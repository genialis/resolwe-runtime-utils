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

import json
import os
import shutil
import socket
import sys
import tempfile
import time

# pylint: disable=missing-docstring
from io import StringIO
from pathlib import Path
from threading import Thread
from unittest import TestCase
from unittest.mock import patch

import requests
import responses

from resolwe_runtime_utils import (
    ImportedFormat,
    _re_annotate_entity_main,
    _re_checkrc_main,
    _re_error_main,
    _re_export_main,
    _re_info_main,
    _re_progress_main,
    _re_save_dir_list_main,
    _re_save_dir_main,
    _re_save_file_list_main,
    _re_save_file_main,
    _re_save_list_main,
    _re_save_main,
    _re_warning_main,
    annotate_entity,
    checkrc,
    error,
    export_file,
    import_file,
    info,
    progress,
    save,
    save_dir,
    save_dir_list,
    save_file,
    save_file_list,
    save_list,
    send_message,
    warning,
)

TEST_ROOT = os.path.abspath(os.path.dirname(__file__))


class ResolweRuntimeUtilsTestCase(TestCase):
    def assertJSONEqual(self, json_, expected_json):  # pylint: disable=invalid-name
        self.assertEqual(json.loads(json_), json.loads(expected_json))


class TestAnnotate(ResolweRuntimeUtilsTestCase):
    def test_annotation(self):
        expected = {'type': 'COMMAND', 'type_data': 'annotate', 'data': {'foo': 0}}
        self.assertEqual(annotate_entity('foo', '0'), expected)


class TestSave(ResolweRuntimeUtilsTestCase):
    def test_number(self):
        expected = {'type': 'COMMAND', 'type_data': 'update_output', 'data': {'foo': 0}}
        self.assertEqual(save('foo', '0'), expected)

    def test_quote(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {'foo': '"'},
        }
        self.assertEqual(save('foo', '"'), expected)

    def test_string(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {'bar': 'baz'},
        }
        self.assertEqual(save('bar', 'baz'), expected)
        expected["data"] = {'proc.warning': 'Warning foo'}
        self.assertEqual(save('proc.warning', 'Warning foo'), expected)
        expected["data"] = {'number': "0"}
        self.assertEqual(save('number', '"0"'), expected)

    @patch('resolwe_runtime_utils.collect_entry', return_value=(1, 1))
    def test_hash(self, collect_mock):
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {'etc': {'file': 'foo.py', "size": 1, "total_size": 2}},
        }
        self.assertEqual(save('etc', '{"file": "foo.py"}'), expected)

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
        expected = {'type': 'COMMAND', 'type_data': 'export_files', 'data': ['foo.txt']}
        self.assertEqual(export_file('foo.txt'), expected)

    @patch('os.path.isfile', return_value=False)
    def test_missing_file(self, isfile_mock):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'error': "Referenced file does not exist: 'foo.txt'."},
        }
        self.assertEqual(
            export_file('foo.txt'),
            expected,
        )

    def test_many_filenames(self):
        self.assertRaises(TypeError, export_file, 'etc', 'foo.txt', 'bar.txt')


class TestSaveList(ResolweRuntimeUtilsTestCase):
    def test_paths(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {'src': ['file1.txt', 'file 2.txt']},
        }
        self.assertEqual(save_list('src', 'file1.txt', 'file 2.txt'), expected)

    def test_urls(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {
                'urls': [
                    {'name': 'View', 'url': 'https://www.google.com'},
                    {'name': 'View', 'url': 'https://www.genialis.com'},
                ]
            },
        }
        self.assertEqual(
            save_list(
                'urls',
                '{"name": "View", "url": "https://www.google.com"}',
                '{"name": "View", "url": "https://www.genialis.com"}',
            ),
            expected,
        )


class TestSaveFile(ResolweRuntimeUtilsTestCase):
    @patch('resolwe_runtime_utils.Path')
    @patch('resolwe_runtime_utils.collect_entry', return_value=(42, 0))
    @patch('os.path.isfile', return_value=True)
    def test_file(self, isfile_mock, collect_mock, path_mock):
        path_mock.is_file.return_value = True
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {'etc': {'file': 'foo.py', 'size': 42, 'total_size': 42}},
        }
        self.assertEqual(save_file('etc', 'foo.py'), expected)
        expected["data"]["etc"]["file"] = "foo bar.py"
        self.assertEqual(save_file('etc', 'foo bar.py'), expected)

    @patch('resolwe_runtime_utils.Path')
    @patch('resolwe_runtime_utils.collect_entry', return_value=(42, 0))
    @patch('os.path.isfile', return_value=True)
    def test_file_with_refs(self, isfile_mock, collect_mock, path_mock):
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {
                'etc': {
                    'file': 'foo.py',
                    'size': 42,
                    'total_size': 42,
                    'refs': ('ref1.txt', 'ref2.txt'),
                }
            },
        }
        self.assertEqual(
            save_file('etc', 'foo.py', 'ref1.txt', 'ref2.txt'),
            expected,
        )

    def test_missing_file(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'error': "Output 'etc' set to a missing file: 'foo.py'."},
        }
        self.assertEqual(
            save_file('etc', 'foo.py'),
            expected,
        )
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'error': "Output 'etc' set to a missing file: 'foo bar.py'."},
        }
        self.assertEqual(save_file('etc', 'foo bar.py'), expected)

    @patch('resolwe_runtime_utils.Path')
    @patch('os.path.isfile', side_effect=[False, False])
    def test_file_with_missing_refs(self, isfile_mock, path_mock):
        path_mock.is_file.return_value = True
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {
                'error': "Output 'src' set to missing references: 'ref1.gz, ref2.gz'."
            },
        }
        self.assertEqual(save_file('src', 'foo.py', 'ref1.gz', 'ref2.gz'), expected)

    def test_improper_input(self):
        self.assertRaises(TypeError, save_file, 'etc')


class TestSaveFileList(ResolweRuntimeUtilsTestCase):
    @patch('resolwe_runtime_utils.collect_entry', side_effect=[(1, 0), (2, 0), (3, 0)])
    @patch('resolwe_runtime_utils.Path')
    def test_files(self, path_mock, collect_mock):
        path_mock.is_file.return_value = True
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {
                'src': [
                    {'file': 'foo.py', 'size': 1, 'total_size': 1},
                    {'file': 'bar 2.py', 'size': 2, 'total_size': 2},
                    {'file': 'baz/3.py', 'size': 3, 'total_size': 3},
                ]
            },
        }
        self.assertEqual(
            save_file_list('src', 'foo.py', 'bar 2.py', 'baz/3.py'), expected
        )

    @patch('resolwe_runtime_utils.collect_entry', side_effect=[(1, 1), (2, 0)])
    @patch('resolwe_runtime_utils.Path')
    @patch('os.path.isfile', return_value=True)
    def test_file_with_refs(self, isfile_mock, path_mock, collect_mock):
        path_mock.is_file.return_value = True
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {
                'src': [
                    {
                        'file': 'foo.py',
                        'size': 1,
                        'total_size': 2,
                        'refs': ['ref1.gz', 'ref2.gz'],
                    },
                    {'file': 'bar.py', 'size': 2, 'total_size': 2},
                ]
            },
        }
        self.assertEqual(
            save_file_list('src', 'foo.py:ref1.gz,ref2.gz', 'bar.py'), expected
        )

    def test_missing_file(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'error': "Output 'src' set to a missing file: 'foo.py'."},
        }
        self.assertEqual(
            save_file_list('src', 'foo.py', 'bar 2.py', 'baz/3.py'), expected
        )

    def test_missing_file_with_refs(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'error': "Output 'src' set to a missing file: 'foo.py'."},
        }
        self.assertEqual(
            save_file_list('src', 'foo.py:ref1.gz,ref2.gz', 'bar.py'), expected
        )

    @patch('resolwe_runtime_utils.collect_entry', side_effect=[(0, 0)])
    @patch('resolwe_runtime_utils.Path')
    @patch('os.path.isfile', side_effect=[False, False])
    def test_file_with_missing_refs(self, isfile_mock, path_mock, collect_mock):
        path_mock.is_file.return_value = True
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {
                'error': "Output 'src' set to missing references: 'ref1.gz, ref2.gz'."
            },
        }
        self.assertEqual(save_file_list('src', 'foo.py:ref1.gz,ref2.gz'), expected)

    def test_files_invalid_format(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'error': "Only one colon ':' allowed in file-refs specification."},
        }
        self.assertEqual(
            save_file_list('src', 'foo.py:ref1.gz:ref2.gz', 'bar.py'),
            expected,
        )


class TestSaveDir(ResolweRuntimeUtilsTestCase):
    @patch('resolwe_runtime_utils.collect_entry', side_effect=[(42, 0), (42, 0)])
    @patch('resolwe_runtime_utils.Path')
    def test_dir(self, path_mock, collect_mock):
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {'etc': {'dir': 'foo', 'size': 42, 'total_size': 42}},
        }
        self.assertEqual(save_dir('etc', 'foo'), expected)
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {'etc': {'dir': 'foo bar', 'size': 42, 'total_size': 42}},
        }
        self.assertEqual(save_dir('etc', 'foo bar'), expected)

    @patch('resolwe_runtime_utils.collect_entry', return_value=(42, 0))
    @patch('resolwe_runtime_utils.Path')
    @patch('os.path.isdir', return_value=True)
    def test_dir_with_refs(self, isdir_mock, path_mock, collect_mock):
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {
                'etc': {
                    'dir': 'foo',
                    'size': 42,
                    'total_size': 42,
                    'refs': ('ref1.txt', 'ref2.txt'),
                }
            },
        }
        self.assertEqual(save_dir('etc', 'foo', 'ref1.txt', 'ref2.txt'), expected)

    def test_missing_dir(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'error': "Output 'etc' set to a missing directory: 'foo'."},
        }
        self.assertEqual(save_dir('etc', 'foo'), expected)
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'error': "Output 'etc' set to a missing directory: 'foo bar'."},
        }
        self.assertEqual(save_dir('etc', 'foo bar'), expected)

    @patch('resolwe_runtime_utils.collect_entry', return_value=(42, 0))
    @patch('resolwe_runtime_utils.Path')
    @patch('os.path.isdir', side_effect=[False, False])
    def test_dir_with_missing_refs(self, isdir_mock, path_mock, collect_mock):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {
                'error': "Output 'etc' set to missing references: 'ref1.gz, ref2.gz'."
            },
        }
        self.assertEqual(save_dir('etc', 'foo', 'ref1.gz', 'ref2.gz'), expected)

    def test_improper_input(self):
        self.assertRaises(TypeError, save_dir, 'etc')


class TestSaveDirList(ResolweRuntimeUtilsTestCase):
    @patch('resolwe_runtime_utils.collect_entry', side_effect=[(1, 0), (2, 0), (3, 0)])
    @patch('resolwe_runtime_utils.Path')
    @patch('os.path.isdir', return_value=True)
    def test_dirs(self, isdir_mock, path_mock, collect_mock):
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {
                'src': [
                    {'dir': 'dir1', 'size': 1, 'total_size': 1},
                    {'dir': 'dir 2', 'size': 2, 'total_size': 2},
                    {'dir': 'dir/3', 'size': 3, 'total_size': 3},
                ]
            },
        }
        self.assertEqual(save_dir_list('src', 'dir1', 'dir 2', 'dir/3'), expected)

    @patch('resolwe_runtime_utils.collect_entry', side_effect=[(1, 0), (2, 0)])
    @patch('resolwe_runtime_utils.Path')
    @patch('os.path.isdir', return_value=True)
    def test_dir_with_refs(self, isdir_mock, path_mock, collect_mock):
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_output',
            'data': {
                'src': [
                    {
                        'dir': 'dir1',
                        'size': 1,
                        'total_size': 1,
                        'refs': ['ref1.gz', 'ref2.gz'],
                    },
                    {'dir': 'dir2', 'size': 2, 'total_size': 2},
                ]
            },
        }
        self.assertEqual(save_dir_list('src', 'dir1:ref1.gz,ref2.gz', 'dir2'), expected)

    def test_missing_dir(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'error': "Output 'src' set to a missing directory: 'dir1'."},
        }
        self.assertEqual(save_dir_list('src', 'dir1', 'dir 2', 'dir/3'), expected)

    @patch('resolwe_runtime_utils.Path')
    @patch('os.path.isdir', side_effect=[False, False])
    def test_dir_with_missing_refs(self, isdir_mock, path_mock):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {
                'error': "Output 'src' set to missing references: 'ref1.gz, ref2.gz'."
            },
        }
        self.assertEqual(save_dir_list('src', 'dir:ref1.gz,ref2.gz'), expected)

    def test_files_invalid_format(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'error': "Only one colon ':' allowed in dir-refs specification."},
        }
        self.assertEqual(
            save_dir_list('src', 'dir1:ref1.bar:ref2.bar', 'dir2'), expected
        )


class TestInfo(ResolweRuntimeUtilsTestCase):
    def test_string(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'info': 'Some info'},
        }
        self.assertEqual(info('Some info'), expected)

    def test_improper_input(self):
        self.assertRaises(TypeError, info, 'First', 'Second')


class TestWarning(ResolweRuntimeUtilsTestCase):
    def test_string(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'warning': 'Some warning'},
        }
        self.assertEqual(warning('Some warning'), expected)

    def test_improper_input(self):
        self.assertRaises(TypeError, warning, 'First', 'Second')


class TestError(ResolweRuntimeUtilsTestCase):
    def test_string(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'error': 'Some error'},
        }
        self.assertEqual(error('Some error'), expected)

    def test_improper_input(self):
        self.assertRaises(TypeError, error, 'First', 'Second')


class TestProgress(ResolweRuntimeUtilsTestCase):
    def test_number(self):
        expected = {'type': 'COMMAND', 'type_data': 'progress', 'data': 10}
        self.assertEqual(progress(0.1), expected)
        expected = {'type': 'COMMAND', 'type_data': 'progress', 'data': 0}
        self.assertEqual(progress(0), expected)
        expected = {'type': 'COMMAND', 'type_data': 'progress', 'data': 100}
        self.assertEqual(progress(1), expected)

    def test_string(self):
        expected = {'type': 'COMMAND', 'type_data': 'progress', 'data': 10}
        self.assertEqual(progress('0.1'), expected)
        expected = {'type': 'COMMAND', 'type_data': 'progress', 'data': 0}
        self.assertEqual(progress('0'), expected)
        expected = {'type': 'COMMAND', 'type_data': 'progress', 'data': 100}
        self.assertEqual(progress('1'), expected)

    def test_bool(self):
        expected = {'type': 'COMMAND', 'type_data': 'progress', 'data': 100}
        self.assertEqual(progress(True), expected)

    def test_improper_input(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'warning': 'Progress must be a float.'},
        }
        self.assertEqual(progress(None), expected)
        self.assertEqual(progress('one'), expected)
        self.assertEqual(progress('[0.1]'), expected)
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'warning': 'Progress must be a float between 0 and 1.'},
        }
        self.assertEqual(progress(-1), expected)
        self.assertEqual(progress(1.1), expected)
        self.assertEqual(progress('1.1'), expected)


class TestCheckRC(ResolweRuntimeUtilsTestCase):
    def test_valid_integers(self):
        expected = {'type': 'COMMAND', 'type_data': 'update_rc', 'data': {'rc': 0}}
        self.assertEqual(checkrc(0), expected)
        self.assertEqual(checkrc(2, 2, 'Error'), expected)
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_rc',
            'data': {'rc': 1, 'error': 'Error'},
        }
        self.assertEqual(checkrc(1, 2, 'Error'), expected)
        expected = {'type': 'COMMAND', 'type_data': 'update_rc', 'data': {'rc': 0}}
        self.assertEqual(checkrc(2, 2), expected)
        expected = {'type': 'COMMAND', 'type_data': 'update_rc', 'data': {'rc': 1}}
        self.assertEqual(checkrc(1, 2), expected)

    def test_valid_strings(self):
        expected = {'type': 'COMMAND', 'type_data': 'update_rc', 'data': {'rc': 0}}
        self.assertEqual(checkrc('0'), expected)
        self.assertEqual(checkrc('2', '2', 'Error'), expected)
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_rc',
            'data': {'rc': 1, 'error': 'Error'},
        }
        self.assertEqual(checkrc('1', '2', 'Error'), expected)

    def test_error_message_not_string(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'update_rc',
            'data': {'rc': 1, 'error': ['Error']},
        }
        self.assertEqual(checkrc(1, ['Error']), expected)

    def test_improper_input(self):
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'error': "Invalid return code: 'None'."},
        }
        self.assertEqual(checkrc(None), expected)
        self.assertEqual(
            checkrc(1, None, 'Error'),
            expected,
        )
        expected = {
            'type': 'COMMAND',
            'type_data': 'process_log',
            'data': {'error': "Invalid return code: 'foo'."},
        }
        self.assertEqual(checkrc('foo'), expected)
        self.assertEqual(
            checkrc(1, 'foo', 'Error'),
            expected,
        )


class SendMessageTest(TestCase):
    def test_send_message(self):
        def _receive(server_socket, result):
            header_size = 8
            response = {'type_data': 'OK'}
            message_body = json.dumps(response).encode()
            message_header = len(message_body).to_bytes(header_size, byteorder="big")
            message = message_header + message_body
            connection = sock.accept()[0]
            received = b""
            header_length = int.from_bytes(
                connection.recv(header_size), byteorder="big"
            )
            received = connection.recv(header_length)
            connection.send(message)
            result.append(received)

        result = []
        test_message = "Test data"
        temp_dir = tempfile.mkdtemp()
        try:
            socket_path = os.path.join(temp_dir, "socket.s")
            with patch("resolwe_runtime_utils.COMMUNICATOR_SOCKET", socket_path):
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.bind(socket_path)
                sock.listen(1)
                server_thread = Thread(target=_receive, args=(sock, result))
                server_thread.start()
                send_message(test_message)
                server_thread.join()
        finally:
            shutil.rmtree(temp_dir)

        self.assertEqual(test_message, json.loads(result[0].decode()))


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

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: x)
    def test_uncompressed(self, send_mock):
        self.assertImportFile(
            'some file.1.txt', 'test uncompressed.txt', 'test uncompressed.txt'
        )

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: x)
    def test_gz(self, send_mock):
        self.assertImportFile('some file.1.txt.gz', 'test gz.txt.gz', 'test gz.txt')

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: x)
    def test_7z(self, send_mock):
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

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: x)
    def test_7z_corrupted(self, send_mock):
        with self.assertRaises(ValueError, msg='failed to extract file: corrupted.zip'):
            import_file(self._file('corrupted.zip'), 'corrupted.zip')

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: x)
    def test_gz_corrupted(self, send_mock):
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
    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: x)
    def test_uncompressed_url(self, send_mock):
        responses.add(
            responses.GET, 'https://testurl/someslug', status=200, body='some text'
        )

        import_file('https://testurl/someslug', 'test uncompressed.txt')
        assert os.path.exists('test uncompressed.txt'), "file not found"
        assert os.path.exists('test uncompressed.txt.gz'), "file not found"

    @responses.activate
    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: x)
    def test_gz_url(self, send_mock):
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
    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: x)
    def test_7z_url(self, send_mock):
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

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: x)
    def test_invalid_url(self, send_mock):
        with self.assertRaises(requests.exceptions.ConnectionError):
            import_file('http://testurl/someslug', 'test uncompressed.txt.zip')


class TestConsoleCommands(ResolweRuntimeUtilsTestCase):
    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_annotate(self, stdout_mock, send_mock):
        with patch.object(sys, 'argv', ['_', 'foo.bar', '2']):
            _re_annotate_entity_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{'type': 'COMMAND', 'type_data': 'annotate', 'data': {'foo.bar': 2}}\n",
            )

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('sys.stdout', new_callable=StringIO)
    def test_error_handling(self, stdout_mock, send_mock):
        with patch.object(sys, 'argv', ['re-save', 'test', '123', 'test', '345']):
            _re_save_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{\'type\': \'COMMAND\', \'type_data\': \'process_log\', \'data\': {\'error\': \"Unexpected error in \'re-save\': save() takes 2 positional arguments but 4 were given\"}}\n",
            )

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_save(self, stdout_mock, send_mock):
        send_mock.side_effect = lambda x: print(x)
        with patch.object(sys, 'argv', ['_', 'foo.bar', '2']):
            _re_save_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{'type': 'COMMAND', 'type_data': 'update_output', 'data': {'foo.bar': 2}}\n",
            )

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('os.path.isfile', return_value=True)
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_export(self, stdout_mock, isfile_mock, send_mock):
        with patch.object(sys, 'argv', ['_', 'foo.bar']):
            _re_export_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{'type': 'COMMAND', 'type_data': 'export_files', 'data': ['foo.bar']}\n",
            )

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_save_list(self, stdout_mock, send_mock):
        with patch.object(sys, 'argv', ['_', 'foo.bar', '2', 'baz']):
            _re_save_list_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{'type': 'COMMAND', 'type_data': 'update_output', 'data': {'foo.bar': [2, 'baz']}}\n",
            )

    @patch('resolwe_runtime_utils.collect_entry', return_value=(42, 0))
    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('resolwe_runtime_utils.Path')
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_save_file(self, stdout_mock, path_mock, send_mock, collect_mock):
        with patch.object(sys, 'argv', ['_', 'foo.bar', 'baz.py']):
            _re_save_file_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{'type': 'COMMAND', 'type_data': 'update_output', 'data': {'foo.bar': {'file': 'baz.py', 'size': 42, 'total_size': 42}}}\n",
            )

    @patch('resolwe_runtime_utils.collect_entry', return_value=(42, 0))
    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('resolwe_runtime_utils.Path')
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_save_file_list(self, stdout_mock, path_mock, send_mock, collect_mock):
        path_mock.is_file.return_value = True
        with patch.object(sys, 'argv', ['_', 'foo.bar', 'baz.py', 'baz 2.py']):
            _re_save_file_list_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{'type': 'COMMAND', 'type_data': 'update_output', 'data': {'foo.bar': [{'file': 'baz.py', 'size': 42, 'total_size': 42}, {'file': 'baz 2.py', 'size': 42, 'total_size': 42}]}}\n",
            )

    @patch('resolwe_runtime_utils.collect_entry', return_value=(42, 0))
    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('resolwe_runtime_utils.Path')
    @patch('os.path.isdir', return_value=True)
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_save_dir(
        self, stdout_mock, isdir_mock, path_mock, send_mock, collect_mock
    ):
        with patch.object(sys, 'argv', ['_', 'foo.bar', 'baz']):
            _re_save_dir_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{'type': 'COMMAND', 'type_data': 'update_output', 'data': {'foo.bar': {'dir': 'baz', 'size': 42, 'total_size': 42}}}\n",
            )

    @patch('resolwe_runtime_utils.collect_entry', return_value=(42, 0))
    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('resolwe_runtime_utils.Path')
    @patch('os.path.isdir', return_value=True)
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_save_dir_list(
        self, stdout_mock, isfile_mock, path_mock, send_mock, collect_mock
    ):
        with patch.object(sys, 'argv', ['_', 'foo.bar', 'baz', 'baz 2']):
            _re_save_dir_list_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{'type': 'COMMAND', 'type_data': 'update_output', 'data': {'foo.bar': [{'dir': 'baz', 'size': 42, 'total_size': 42}, {'dir': 'baz 2', 'size': 42, 'total_size': 42}]}}\n",
            )

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_info(self, stdout_mock, send_mock):
        with patch.object(sys, 'argv', ['_', 'some info']):
            _re_info_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{'type': 'COMMAND', 'type_data': 'process_log', 'data': {'info': 'some info'}}\n",
            )

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_warning(self, stdout_mock, send_mock):
        with patch.object(sys, 'argv', ['_', 'some warning']):
            _re_warning_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{'type': 'COMMAND', 'type_data': 'process_log', 'data': {'warning': 'some warning'}}\n",
            )

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_error(self, stdout_mock, send_mock):
        with patch.object(sys, 'argv', ['_', 'some error']):
            _re_error_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{'type': 'COMMAND', 'type_data': 'process_log', 'data': {'error': 'some error'}}\n",
            )

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_progress(self, stdout_mock, send_mock):
        with patch.object(sys, 'argv', ['_', '0.7']):
            _re_progress_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{'type': 'COMMAND', 'type_data': 'progress', 'data': 70}\n",
            )

    @patch('resolwe_runtime_utils.send_message', side_effect=lambda x: print(x))
    @patch('sys.stdout', new_callable=StringIO)
    def test_re_checkrc(self, stdout_mock, send_mock):
        with patch.object(sys, 'argv', ['_', '1', '2', 'error']):
            _re_checkrc_main()
            self.assertEqual(
                stdout_mock.getvalue(),
                "{'type': 'COMMAND', 'type_data': 'update_rc', 'data': {'rc': 1, 'error': 'error'}}\n",
            )
