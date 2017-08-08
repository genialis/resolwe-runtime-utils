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

"""
Utility functions that make it easier to write a Resolwe process.
"""

import json
import os

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


def export(file_path):
    """Prepend the given parameter with ``export``"""

    if not os.path.isfile(file_path):
        return error("Referenced file does not exist: '{}'.".format(file_path))

    return "export {}".format(file_path)


def save_list(key, *values):
    """Convert the given list of parameters to a JSON object.

    JSON object is of the form:
    { key: [values[0], values[1], ... ] },
    where values represent the given list of parameters.

    """
    return json.dumps({key: [_get_json(value) for value in values]})


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
        missing_refs = [ref for ref in refs if not (os.path.isfile(ref) or os.path.isdir(ref))]
        if len(missing_refs) > 0:
            return error("Output '{}' set to missing references: '{}'.".format(
                key, ', '.join(missing_refs)))
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
            return error("Output '{}' set to a missing file: '{}'.".format(key, file_name))
        file_obj = {'file': file_name}

        if refs:
            refs = [ref_path.strip() for ref_path in refs.split(',')]
            missing_refs = [ref for ref in refs if not (os.path.isfile(ref) or os.path.isdir(ref))]
            if len(missing_refs) > 0:
                return error("Output '{}' set to missing references: '{}'.".format(
                    key, ', '.join(missing_refs)))
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
        return error("Output '{}' set to a missing directory: '{}'.".format(key, dir_path))

    result = {key: {"dir": dir_path}}

    if refs:
        missing_refs = [ref for ref in refs if not (os.path.isfile(ref) or os.path.isdir(ref))]
        if len(missing_refs) > 0:
            return error("Output '{}' set to missing references: '{}'.".format(
                key, ', '.join(missing_refs)))
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
            return error("Output '{}' set to a missing directory: '{}'.".format(key, dir_path))
        dir_obj = {'dir': dir_path}

        if refs:
            refs = [ref_path.strip() for ref_path in refs.split(',')]
            missing_refs = [ref for ref in refs if not (os.path.isfile(ref) or os.path.isdir(ref))]
            if len(missing_refs) > 0:
                return error("Output '{}' set to missing references: '{}'.".format(
                    key, ', '.join(missing_refs)))
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


def _re_save_main():
    _re_generic_main(save)


def _re_export_main():
    _re_generic_main(export)


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
