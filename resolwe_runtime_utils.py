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
import functools
import glob
import gzip
import json
import logging
import os
import re
import shlex
import shutil
import socket
import subprocess
import tarfile
import time
import zlib
from contextlib import suppress
from enum import Enum
from itertools import zip_longest
from pathlib import Path

# Socket constants. The timeout is set to infinite.
SOCKET_TIMEOUT = None
if "SOCKET_TIMEOUT" in os.environ:
    SOCKET_TIMEOUT = int(os.environ["SOCKET_TIMEOUT"])

SOCKETS_PATH = Path(os.environ.get("SOCKETS_VOLUME", "/sockets"))
COMMUNICATOR_SOCKET = SOCKETS_PATH / os.environ.get("SCRIPT_SOCKET", "_socket2.s")
DATA_VOLUME = Path(os.environ.get("DATA_VOLUME", "/data"))

# Upload files in batches of 1000.
UPLOAD_FILE_BATCH_SIZE = 1000

logger = logging.getLogger(__name__)


# Compat between Python 2.7/3.4 and Python 3.5
if not hasattr(json, 'JSONDecodeError'):
    json.JSONDecodeError = ValueError


OutputType = Enum("OutputType", "Value FileDir Storage")


def _retry(
    max_retries=5,
    retry_exceptions=(ConnectionError, FileNotFoundError),
    min_sleep=1,
    max_sleep=10,
):
    """Try to call decorated method max_retries times before giving up.

    The calls are retried when function raises exception in retry_exceptions.

    :param max_retries: maximal number of calls before giving up.
    :param retry_exceptions: retry call if one of these exceptions is raised.
    :param min_sleep: minimal sleep between calls (in seconds).
    :param max_sleep: maximal sleep between calls (in seconds).
    :returns: return value of the called method.
    :raises: the last exceptions raised by the method call if none of the
      retries were successfull.
    """

    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper_retry(*args, **kwargs):
            last_error = Exception("Retry failed")
            sleep = 0
            for retry in range(max_retries):
                try:
                    time.sleep(sleep)
                    return func(*args, **kwargs)
                except retry_exceptions as err:
                    sleep = min(max_sleep, min_sleep * (2**retry))
                    last_error = err
            raise last_error

        return wrapper_retry

    return decorator_retry


def _read_bytes(socket, message_size):
    """Read message_size bytes from the given socket.

    The method will block until enough bytes are available.

    :param socket: the socket to read from.
    :param message_size: size (in bytes) of the message to read.
    :returns: received message.
    """
    message = b""
    while len(message) < message_size:
        received = socket.recv(message_size - len(message))
        message += received
        if not received:
            return message
    return message


def _receive_data(socket, header_size=8):
    """Recieve data over the given socket.

    :param socket: the socket to read from.
    :param header_size: how first many bytes in message are dedicated to the
        message size (pre-padded with zeros).
    """
    message = _read_bytes(socket, header_size)
    if not message:
        return None
    message_size = int.from_bytes(message, byteorder="big")
    message = _read_bytes(socket, message_size)
    assert len(message) == message_size
    data = json.loads(message.decode("utf-8"))
    return data


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


def command(name, data):
    """Create a command from command name and payload."""
    return {"type": "COMMAND", "type_data": name, "data": data}


def send_message(data, header_size=8):
    """Send data over socket."""

    @_retry()
    def _connect(socket_path):
        """Connect socket."""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        sock.settimeout(SOCKET_TIMEOUT)
        return sock

    def _check_response(response):
        if response is None:
            raise RuntimeError(
                "No response received when sending message: {}.".format(data)
            )

        if "type_data" not in response:
            raise ValueError(
                "Response {} does not contain key 'type_data'.".format(response)
            )

        return response["type_data"] == "OK"

    try:
        sock = _connect(str(COMMUNICATOR_SOCKET))
        message = json.dumps(data).encode()
        message_length = len(message).to_bytes(header_size, byteorder="big")
        sock.sendall(message_length)
        sock.sendall(message)
        response = _receive_data(sock)
        if not _check_response(response):
            logger.error("Error in respone to %s: %s.", data, response)
            raise RuntimeError("Wrong response received, terminating processing.")

    finally:
        sock.close()
        return response


def collect_entry(entry, references):
    """Get the size of the entry and its references and upload them.

    The entry and its references are uploaded to the chosen storage connector.

    NOTE: This process may take considerable amount of time.

    :args entry: file or directory that is being collected.
    :args references: references belonging to the entry.
    """

    def grouper(iterable, n, fillvalue=None):
        """Collect data into fixed-length chunks or blocks.

        See https://docs.python.org/3/library/itertools.html#itertools-recipes.
        """
        args = [iter(iterable)] * n
        return zip_longest(*args, fillvalue=fillvalue)

    def get_entries_size(entries, processed_files, processed_dirs):
        """Get the total size of the entries.

        Traverse all the files and add their sizes. Skip already processed
        fles: is a common case that the file itself is also referenced under
        references for instance.

        :raises RuntimeError: when one of the entris is neither file nor
            directory.
        """
        total_size = 0
        for entry in entries:
            if entry in processed_files:
                continue
            elif entry.is_dir():
                processed_dirs.add(entry)
                total_size += get_entries_size(
                    entry.glob("*"), processed_files, processed_dirs
                )
            elif entry.is_file():
                processed_files.add(entry)
                total_size += entry.stat().st_size
            else:
                raise RuntimeError(
                    "While collecting entries: {} must be either file of directory.".format(
                        entry
                    )
                )
        return total_size

    processed_dirs = set()
    processed_files = set()
    entry_path = Path(entry)
    entry_size = get_entries_size([entry_path], processed_files, processed_dirs)
    references_size = get_entries_size(
        (Path(reference) for reference in references), processed_files, processed_dirs
    )
    # Upload files in chunks. If possible avoid creation of a giant
    # list when number of referenced files is huge: its size could be
    # over half a milion in special cases.
    for group in grouper(processed_files, UPLOAD_FILE_BATCH_SIZE):
        send_message(
            command(
                "upload_files",
                [str(entry) for entry in group if entry is not None],
            )
        )
    for group in grouper(processed_dirs, UPLOAD_FILE_BATCH_SIZE):
        send_message(
            command(
                "upload_dirs",
                [str(entry) for entry in group if entry is not None],
            )
        )
    return (entry_size, references_size)


def _determine_value_type(value):
    """Determine the type of the output value.

    This is mostly playing hide and seek with the old code. Sometimes the
    files and directories are stored via save_file/dir methods and sometimes
    the plain save is used with value being JSON dict representing file/dir.

    In addition the name of the file could be stored in a value as a string.
    In such case the expected behaviour is to read the content of referenced
    file and send it instead.
    """
    determined_type = OutputType.Value
    if isinstance(value, dict) and any(entry in value for entry in ("file", "dir")):
        determined_type = OutputType.FileDir
    elif isinstance(value, str) and Path(value).is_file():
        determined_type = OutputType.Storage
    return determined_type


def _preprocess_data(data):
    """Preprocess data accordind to its guessed type.

    In case of file/dir add their size/total_size to the dictionary.
    In case of storage send the file content instead of filename.
    """
    value_type = _determine_value_type(data)
    if value_type == OutputType.FileDir:
        filedir_key = "file" if "file" in data else "dir"
        entry_size, refs_size = collect_entry(data[filedir_key], data.get("refs", []))
        data["size"] = entry_size
        data["total_size"] = entry_size + refs_size

    # When saving 'storage' the second argument is a path to the JSON file.
    # Copy the file to the shared filespace and hope there are not a lot of
    # false hits.
    elif value_type == OutputType.Storage:
        try:
            file_content = Path(data).read_text()
            data = json.loads(file_content)
        except json.JSONDecodeError:
            raise RuntimeError(
                "Value must be a valid JSON, current: {}".format(file_content)
            )
    return data


def _get_dir_size(path):
    """Get directory size.

    :param path: a Path object pointing to the directory.
    :type path: pathlib.Path
    """
    return sum(
        file_.stat().st_size for file_ in Path(path).rglob("*") if file_.is_file()
    )


def save_list(key, *values):
    """Construct save_list command."""
    return command(
        "update_output",
        {key: [_preprocess_data(_get_json(value)) for value in values]},
    )


def annotate_entity(key, value):
    """Construct annotate entity command."""
    return command("annotate", {key: _get_json(value)})


def save(key, value):
    """Construct save command."""
    return command("update_output", {key: _preprocess_data(_get_json(value))})


def save_file(key, file_path, *refs):
    """Construct save file command.

    Data is of the form:
    { key: {"file": file_path, "size": file_size, "total_size": total_size }}

    with added references

    "refs": [refs[0], refs[1], ... ]

    when applicable.
    """
    path = Path(file_path)
    if not path.is_file():
        return error("Output '{}' set to a missing file: '{}'.".format(key, file_path))

    data = {"file": file_path}

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
        data['refs'] = refs
    entry_size, refs_size = collect_entry(data["file"], data.get("refs", []))
    data["size"] = entry_size
    data["total_size"] = entry_size + refs_size
    return command("update_output", {key: data})


def save_file_list(key, *files_refs):
    """Construct the save files command.

    Each parameter is a file-refs specification of the form:
    <file-path>:<reference1>,<reference2>, ...,
    where the colon ':' and the list of references are optional.

    Data object is of the form:
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
        path = Path(file_name)
        if not path.is_file():
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

    for data in file_list:
        entry_size, refs_size = collect_entry(data["file"], data.get("refs", []))
        data["size"] = entry_size
        data["total_size"] = entry_size + refs_size
    return command("update_output", {key: file_list})


def save_dir(key, dir_path, *refs):
    """Construct save dir command.

    Data object is of the form:
    { key: {"dir": dir_path}}, or
    { key: {"dir": dir_path, "refs": [refs[0], refs[1], ... ]}}

    """
    path = Path(dir_path)
    if not path.is_dir():
        return error(
            "Output '{}' set to a missing directory: '{}'.".format(key, dir_path)
        )

    result = {key: {"dir": dir_path, "size": _get_dir_size(path)}}

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

    entry_size, refs_size = collect_entry(
        result[key]["dir"], result[key].get("refs", [])
    )
    result[key]["size"] = entry_size
    result[key]["total_size"] = entry_size + refs_size
    return command("update_output", result)


def save_dir_list(key, *dirs_refs):
    """Construct save dirs command.

    Each parameter is a dir-refs specification of the form:
    <dir-path>:<reference1>,<reference2>, ...,
    where the colon ':' and the list of references are optional.

    Data object is of the form:
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

        path = Path(dir_path)
        if not path.is_dir():
            return error(
                "Output '{}' set to a missing directory: '{}'.".format(key, dir_path)
            )
        dir_obj = {'dir': dir_path, "size": _get_dir_size(path)}

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

    for data in dir_list:
        entry_size, refs_size = collect_entry(data["dir"], data.get("refs", []))
        data["size"] = entry_size
        data["total_size"] = entry_size + refs_size
    return command("update_output", {key: dir_list})


def _process_log(type, value):
    """Construct general process_log command."""
    return command("process_log", {type: value})


def info(value):
    """Construct info command."""
    return _process_log("info", value)


def warning(value):
    """Construct warning command."""
    return _process_log("warning", value)


def error(value):
    """Construct error command."""
    return _process_log("error", value)


def progress(progress):
    """Construct progress command.

    Progress is reported as float between 0 and 1 and sent to listener as int
    between 0 and 100.
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

    return command("progress", round(progress * 100))


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

    changes = {"rc": rc}
    if rc and error_msg:
        changes["error"] = error_msg

    return command("update_rc", changes)


def export_file(file_path):
    """Construct export command."""

    if not os.path.isfile(file_path):
        return error("Referenced file does not exist: '{}'.".format(file_path))

    return command("export_files", [file_path])


def run(process_slug, run):
    """Run process with the given slug with the given inputs.

    The argument run must be a valid JSON string representing the inputs.
    """
    return command("run", {"process": process_slug, "input": _get_json(run)})


CHUNK_SIZE = 10000000  # 10 Mbytes


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

    import requests

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
        # Resolve url.
        src = send_message(command("resolve_url", src))["data"]

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
                        send_message(progress(next_progress))
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
        send_message(progress(progress_to))

    return destination_file_name


###############################################################################
# Auxiliary functions for preparing multi-platform console scripts via        #
# setuptools' 'console_scripts' entry points mechanism for automatic script   #
# creation.                                                                   #
###############################################################################


def _re_generic_main(fn):
    """Main method."""
    import sys

    try:
        data = fn(*sys.argv[1:])
    except Exception as exc:
        logger.exception("Exception in resolwe-runtime-utils.")
        data = error("Unexpected error in '{}': {}".format(sys.argv[0], exc))
    # Send data to the communication container.
    send_message(data)


def _re_annotate_entity_main():
    _re_generic_main(annotate_entity)


def _re_save_main():
    _re_generic_main(save)


def _re_run_main():
    _re_generic_main(run)


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
