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


def _get_json(value):
    """Convert the given value to a JSON object."""
    if hasattr(value, 'replace'):
        value = value.replace('\n', ' ')
    try:
        return json.loads(value)
    except ValueError:
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


def save_file(key, file_name, *refs):
    """Convert the given parameters to a special JSON object.

    JSON object is of the form:
    { key: {"file": file_name}}, or
    { key: {"file": file_name, "refs": [refs[0], refs[1], ... ]}} if refs are
    given.

    """
    if not os.path.isfile(file_name):
        return error("Output '{}' set to a missing file: '{}'.".format(key, file_name))
    result = {key: {'file': file_name}}

    if refs:
        missing_refs = [ref for ref in refs if not (os.path.isfile(ref) or os.path.isdir(ref))]
        if len(missing_refs) > 0:
            return error("Output '{}' set to missing references: '{}'.".format(
                key, ', '.join(missing_refs)))
        result[key]['refs'] = refs

    return json.dumps(result)


def save_file_list(key, *files):
    """Convert the given parameters to a special JSON object.

    Comma-separated Refs are assigned to files using colon:
    e.g. file_name:refs1,refs2

    JSON object is of the form:
    { key: {"file": file_name}}, or
    { key: {"file": file_name, "refs": [refs[0], refs[1], ... ]}} if refs are
    given.

    """
    file_list = []
    for file_name in files:
        if not os.path.isfile(file_name):
            return error("Output '{}' set to a missing file: '{}'.".format(key, file_name))
        vals = file_name.split(':')
        file_obj = {'file': vals[0]}

        if len(vals) == 2:
            refs = [ref_path.strip() for ref_path in vals[1].split(',')]
            missing_refs = [ref for ref in refs if not (os.path.isfile(ref) or os.path.isdir(ref))]
            if len(missing_refs) > 0:
                return error("Output '{}' set to missing references: '{}'.".format(
                    key, ', '.join(missing_refs)))
            file_obj['refs'] = refs
        elif len(vals) >= 2:
            return error("Only one colon ':' allowed in file.")

        file_list.append(file_obj)

    return json.dumps({key: file_list})


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
    if isinstance(progress, str):
        try:
            progress = json.loads(progress)
        except ValueError:
            return warning("Progress must be float.")

    if isinstance(progress, int):
        # cast to int first because bool isinstance int
        progress = float(int(progress))
    elif not isinstance(progress, float):
        return warning("Progress must be float.")

    if not 0 <= float(progress) <= 1:
        return warning("Progress must be float between 0 and 1.")

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
    except TypeError:
        return error("Return code must be integer.")

    acceptable_rcs = []
    error_msg = ""

    if len(args):
        for code in args[:-1]:
            try:
                acceptable_rcs.append(int(code))
            except ValueError:
                return error("Return codes must be integers.")

        try:
            acceptable_rcs.append(int(args[-1]))
        except ValueError:
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
    print(fn(*sys.argv[1:]))


def _re_save_main():
    _re_generic_main(save)


def _re_save_list_main():
    _re_generic_main(save_list)


def _re_save_file_main():
    _re_generic_main(save_file)


def _re_save_file_list_main():
    _re_generic_main(save_file_list)


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
