# pylint: disable=missing-docstring
import json
from unittest import TestCase

from resolwe_runtime_utils import (
        save, save_file, error, warning, info, progress, checkrc
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
