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

"""
Utility functions that make it easier to write a Resolwe process.
"""
import glob
import gzip
import json
import os
import re
import shlex
import shutil
import subprocess
import tarfile
import zlib

import requests


# Compat between Python 2.7/3.4 and Python 3.5
if not hasattr(json, 'JSONDecodeError'):
    json.JSONDecodeError = ValueError


def _get_json(value):
    """Convert the given value to a JSON object."""
    if hasattr(value, 'replace'):
        value = value.replace('\n', ' ')
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        # Escape double quotes.
        if hasattr(value, 'replace'):
            value = value.replace('"', '\\"')
        # try putting the value into a string
        return json.loads('"{}"'.format(value))


def save(key, value):
    """Convert the given parameters to a JSON object.

    JSON object is of the form:
    { key: value },
    where value can represent any JSON object.

    """
    return json.dumps({key: _get_json(value)})


def save_list(key, *values):
    """Convert the given list of parameters to a JSON object.

    JSON object is of the form:
    { key: [values[0], values[1], ... ] },
    where values represent the given list of parameters.

    """
    return json.dumps({key: [_get_json(value) for value in values]})


def annotate_entity(key, value):
    """
    Convert the given annotation to a JSON object.

    JSON object is of the form:
    { f"_entity.descriptor.{key}": value}.

    """
    return save("_entity.descriptor.{}".format(key), value)


def save_file(key, file_path, *refs):
    """Convert the given parameters to a special JSON object.

    JSON object is of the form:
    { key: {"file": file_path}}, or
    { key: {"file": file_path, "refs": [refs[0], refs[1], ... ]}}

    """
    if not os.path.isfile(file_path):
        return error("Output '{}' set to a missing file: '{}'.".format(key, file_path))

    result = {key: {"file": file_path}}

    if refs:
        missing_refs = [
            ref for ref in refs if not (os.path.isfile(ref) or os.path.isdir(ref))
        ]
        if len(missing_refs) > 0:
            return error(
                "Output '{}' set to missing references: '{}'.".format(
                    key, ', '.join(missing_refs)
                )
            )
        result[key]['refs'] = refs

    return json.dumps(result)


def save_file_list(key, *files_refs):
    """Convert the given parameters to a special JSON object.

    Each parameter is a file-refs specification of the form:
    <file-path>:<reference1>,<reference2>, ...,
    where the colon ':' and the list of references are optional.

    JSON object is of the form:
    { key: {"file": file_path}}, or
    { key: {"file": file_path, "refs": [refs[0], refs[1], ... ]}}

    """
    file_list = []
    for file_refs in files_refs:
        if ':' in file_refs:
            try:
                file_name, refs = file_refs.split(':')
            except ValueError as e:
                return error("Only one colon ':' allowed in file-refs specification.")
        else:
            file_name, refs = file_refs, None
        if not os.path.isfile(file_name):
            return error(
                "Output '{}' set to a missing file: '{}'.".format(key, file_name)
            )
        file_obj = {'file': file_name}

        if refs:
            refs = [ref_path.strip() for ref_path in refs.split(',')]
            missing_refs = [
                ref for ref in refs if not (os.path.isfile(ref) or os.path.isdir(ref))
            ]
            if len(missing_refs) > 0:
                return error(
                    "Output '{}' set to missing references: '{}'.".format(
                        key, ', '.join(missing_refs)
                    )
                )
            file_obj['refs'] = refs

        file_list.append(file_obj)

    return json.dumps({key: file_list})


def save_dir(key, dir_path, *refs):
    """Convert the given parameters to a special JSON object.

    JSON object is of the form:
    { key: {"dir": dir_path}}, or
    { key: {"dir": dir_path, "refs": [refs[0], refs[1], ... ]}}

    """
    if not os.path.isdir(dir_path):
        return error(
            "Output '{}' set to a missing directory: '{}'.".format(key, dir_path)
        )

    result = {key: {"dir": dir_path}}

    if refs:
        missing_refs = [
            ref for ref in refs if not (os.path.isfile(ref) or os.path.isdir(ref))
        ]
        if len(missing_refs) > 0:
            return error(
                "Output '{}' set to missing references: '{}'.".format(
                    key, ', '.join(missing_refs)
                )
            )
        result[key]["refs"] = refs

    return json.dumps(result)


def save_dir_list(key, *dirs_refs):
    """Convert the given parameters to a special JSON object.

    Each parameter is a dir-refs specification of the form:
    <dir-path>:<reference1>,<reference2>, ...,
    where the colon ':' and the list of references are optional.

    JSON object is of the form:
    { key: {"dir": dir_path}}, or
    { key: {"dir": dir_path, "refs": [refs[0], refs[1], ... ]}}

    """
    dir_list = []
    for dir_refs in dirs_refs:
        if ':' in dir_refs:
            try:
                dir_path, refs = dir_refs.split(':')
            except ValueError as e:
                return error("Only one colon ':' allowed in dir-refs specification.")
        else:
            dir_path, refs = dir_refs, None
        if not os.path.isdir(dir_path):
            return error(
                "Output '{}' set to a missing directory: '{}'.".format(key, dir_path)
            )
        dir_obj = {'dir': dir_path}

        if refs:
            refs = [ref_path.strip() for ref_path in refs.split(',')]
            missing_refs = [
                ref for ref in refs if not (os.path.isfile(ref) or os.path.isdir(ref))
            ]
            if len(missing_refs) > 0:
                return error(
                    "Output '{}' set to missing references: '{}'.".format(
                        key, ', '.join(missing_refs)
                    )
                )
            dir_obj['refs'] = refs

        dir_list.append(dir_obj)

    return json.dumps({key: dir_list})


def info(value):
    """Call ``save`` function with "proc.info" as key."""
    return save('proc.info', value)


def warning(value):
    """Call ``save`` function with "proc.warning" as key."""
    return save('proc.warning', value)


def error(value):
    """Call ``save`` function with "proc.error" as key."""
    return save('proc.error', value)


def progress(progress):
    """Convert given progress to a JSON object.

    Check that progress can be represented as float between 0 and 1 and
    return it in JSON of the form:

        {"proc.progress": progress}

    """
    if isinstance(progress, int) or isinstance(progress, float):
        progress = float(progress)
    else:
        try:
            progress = float(json.loads(progress))
        except (TypeError, ValueError):
            return warning("Progress must be a float.")

    if not 0 <= progress <= 1:
        return warning("Progress must be a float between 0 and 1.")

    return json.dumps({'proc.progress': progress})


def checkrc(rc, *args):
    """Check if ``rc`` (return code) meets requirements.

    Check if ``rc`` is 0 or is in ``args`` list that contains
    acceptable return codes.
    Last argument of ``args`` can optionally be error message that
    is printed if ``rc`` doesn't meet requirements.

    Output is JSON of the form:

        {"proc.rc": <rc>,
         "proc.error": "<error_msg>"},

    where "proc.error" entry is omitted if empty.

    """
    try:
        rc = int(rc)
    except (TypeError, ValueError):
        return error("Invalid return code: '{}'.".format(rc))

    acceptable_rcs = []
    error_msg = ""

    if len(args):
        for code in args[:-1]:
            try:
                acceptable_rcs.append(int(code))
            except (TypeError, ValueError):
                return error("Invalid return code: '{}'.".format(code))

        try:
            acceptable_rcs.append(int(args[-1]))
        except (TypeError, ValueError):
            error_msg = args[-1]

    if rc in acceptable_rcs:
        rc = 0

    ret = {'proc.rc': rc}
    if rc and error_msg:
        ret['proc.error'] = error_msg

    return json.dumps(ret)


def export_file(file_path):
    """Prepend the given parameter with ``export``"""

    if not os.path.isfile(file_path):
        return error("Referenced file does not exist: '{}'.".format(file_path))

    return "export {}".format(file_path)


CHUNK_SIZE = 10_000_000  # 10 Mbytes


class ImportedFormat:
    """Import destination file format."""

    EXTRACTED = 'extracted'
    COMPRESSED = 'compressed'
    BOTH = 'both'


def import_file(
    src,
    file_name,
    imported_format=ImportedFormat.BOTH,
    progress_from=0.0,
    progress_to=None,
):
    """Import file to working directory.

    :param src: Source file path or URL
    :param file_name: Source file name
    :param imported_format: Import file format (extracted, compressed or both)
    :param progress_from: Initial progress value
    :param progress_to: Final progress value
    :return: Destination file path (if extracted and compressed, extracted path given)
    """

    if progress_to is not None:
        if not isinstance(progress_from, float) or not isinstance(progress_to, float):
            raise ValueError("Progress_from and progress_to must be float")

        if progress_from < 0 or progress_from > 1:
            raise ValueError("Progress_from must be between 0 and 1")

        if progress_to < 0 or progress_to > 1:
            raise ValueError("Progress_to must be between 0 and 1")

        if progress_from >= progress_to:
            raise ValueError("Progress_to must be higher than progress_from")

    print("Importing and compressing {}...".format(file_name))

    def importGz():
        """Import gzipped file.

        The file_name must have .gz extension.
        """
        if imported_format != ImportedFormat.COMPRESSED:  # Extracted file required
            with open(file_name[:-3], 'wb') as f_out, gzip.open(src, 'rb') as f_in:
                try:
                    shutil.copyfileobj(f_in, f_out, CHUNK_SIZE)
                except zlib.error:
                    raise ValueError("Invalid gzip file format: {}".format(file_name))

        else:  # Extracted file not-required
            # Verify the compressed file.
            with gzip.open(src, 'rb') as f:
                try:
                    while f.read(CHUNK_SIZE) != b'':
                        pass
                except zlib.error:
                    raise ValueError("Invalid gzip file format: {}".format(file_name))

        if imported_format != ImportedFormat.EXTRACTED:  # Compressed file required
            try:
                shutil.copyfile(src, file_name)
            except shutil.SameFileError:
                pass  # Skip copy of downloaded files

        if imported_format == ImportedFormat.COMPRESSED:
            return file_name
        else:
            return file_name[:-3]

    def import7z():
        """Import compressed file in various formats.

        Supported extensions: .bz2, .zip, .rar, .7z, .tar.gz, and .tar.bz2.
        """
        extracted_name, _ = os.path.splitext(file_name)
        destination_name = extracted_name
        temp_dir = 'temp_{}'.format(extracted_name)

        cmd = '7z x -y -o{} {}'.format(shlex.quote(temp_dir), shlex.quote(src))
        try:
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError as err:
            if err.returncode == 2:
                raise ValueError("Failed to extract file: {}".format(file_name))
            else:
                raise

        paths = os.listdir(temp_dir)
        if len(paths) == 1 and os.path.isfile(os.path.join(temp_dir, paths[0])):
            # Single file in archive.
            temp_file = os.path.join(temp_dir, paths[0])

            if imported_format != ImportedFormat.EXTRACTED:  # Compressed file required
                with open(temp_file, 'rb') as f_in, gzip.open(
                    extracted_name + '.gz', 'wb'
                ) as f_out:
                    shutil.copyfileobj(f_in, f_out, CHUNK_SIZE)

            if imported_format != ImportedFormat.COMPRESSED:  # Extracted file required
                shutil.move(temp_file, './{}'.format(extracted_name))

                if extracted_name.endswith('.tar'):
                    with tarfile.open(extracted_name) as tar:
                        tar.extractall()

                    os.remove(extracted_name)
                    destination_name, _ = os.path.splitext(extracted_name)
            else:
                destination_name = extracted_name + '.gz'
        else:
            # Directory or several files in archive.
            if imported_format != ImportedFormat.EXTRACTED:  # Compressed file required
                with tarfile.open(extracted_name + '.tar.gz', 'w:gz') as tar:
                    for fname in glob.glob(os.path.join(temp_dir, '*')):
                        tar.add(fname, os.path.basename(fname))

            if imported_format != ImportedFormat.COMPRESSED:  # Extracted file required
                for path in os.listdir(temp_dir):
                    shutil.move(os.path.join(temp_dir, path), './{}'.format(path))
            else:
                destination_name = extracted_name + '.tar.gz'

        shutil.rmtree(temp_dir)
        return destination_name

    def importUncompressed():
        """Import uncompressed file."""
        if imported_format != ImportedFormat.EXTRACTED:  # Compressed file required
            with open(src, 'rb') as f_in, gzip.open(file_name + '.gz', 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out, CHUNK_SIZE)

        if imported_format != ImportedFormat.COMPRESSED:  # Extracted file required
            try:
                shutil.copyfile(src, file_name)
            except shutil.SameFileError:
                pass  # Skip copy of downloaded files

        return (
            file_name + '.gz'
            if imported_format == ImportedFormat.COMPRESSED
            else file_name
        )

    # Large file download from Google Drive requires cookie and token.
    try:
        response = None
        if re.match(
            r'^https://drive.google.com/[-A-Za-z0-9\+&@#/%?=~_|!:,.;]*[-A-Za-z0-9\+&@#/%=~_|]$',
            src,
        ):
            session = requests.Session()
            response = session.get(src, stream=True)

            token = None
            for key, value in response.cookies.items():
                if key.startswith('download_warning'):
                    token = value
                    break

            if token is not None:
                params = {'confirm': token}
                response = session.get(src, params=params, stream=True)

        elif re.match(
            r'^(https?|ftp)://[-A-Za-z0-9\+&@#/%?=~_|!:,.;]*[-A-Za-z0-9\+&@#/%=~_|]$',
            src,
        ):
            response = requests.get(src, stream=True)
    except requests.exceptions.ConnectionError:
        raise requests.exceptions.ConnectionError("Could not connect to {}".format(src))

    if response:
        with open(file_name, 'wb') as f:
            total = response.headers.get('content-length')
            total = float(total) if total else None
            downloaded = 0
            current_progress = 0
            for content in response.iter_content(chunk_size=CHUNK_SIZE):
                f.write(content)

                if total is not None and progress_to is not None:
                    downloaded += len(content)
                    progress_span = progress_to - progress_from
                    next_progress = progress_from + progress_span * downloaded / total
                    next_progress = round(next_progress, 2)

                    if next_progress > current_progress:
                        print(progress(next_progress))
                        current_progress = next_progress

        # Check if a temporary file exists.
        if not os.path.isfile(file_name):
            raise ValueError("Downloaded file not found {}".format(file_name))

        src = file_name
    else:
        if not os.path.isfile(src):
            raise ValueError("Source file not found {}".format(src))

    # Decide which import should be used.
    if re.search(r'\.(bz2|zip|rar|7z|tgz|tar\.gz|tar\.bz2)$', file_name):
        destination_file_name = import7z()
    elif file_name.endswith('.gz'):
        destination_file_name = importGz()
    else:
        destination_file_name = importUncompressed()

    if progress_to is not None:
        print(progress(progress_to))

    return destination_file_name


###############################################################################
# Auxiliary functions for preparing multi-platform console scripts via        #
# setuptools' 'console_scripts' entry points mechanism for automatic script   #
# creation.                                                                   #
###############################################################################


def _re_generic_main(fn):
    import sys

    try:
        print(fn(*sys.argv[1:]))
    except Exception as exc:
        print(error("Unexpected error in '{}': {}".format(sys.argv[0], exc)))


def _re_annotate_entity_main():
    _re_generic_main(annotate_entity)


def _re_save_main():
    _re_generic_main(save)


def _re_export_main():
    _re_generic_main(export_file)


def _re_save_list_main():
    _re_generic_main(save_list)


def _re_save_file_main():
    _re_generic_main(save_file)


def _re_save_file_list_main():
    _re_generic_main(save_file_list)


def _re_save_dir_main():
    _re_generic_main(save_dir)


def _re_save_dir_list_main():
    _re_generic_main(save_dir_list)


def _re_warning_main():
    _re_generic_main(warning)


def _re_error_main():
    _re_generic_main(error)


def _re_info_main():
    _re_generic_main(info)


def _re_progress_main():
    _re_generic_main(progress)


def _re_checkrc_main():
    _re_generic_main(checkrc)
