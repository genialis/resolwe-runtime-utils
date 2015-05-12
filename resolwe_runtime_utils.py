"""
Utility functions that make it easier to write a Resolwe process.
"""

import json


def save(key, value):
    """Convert the given parameters to a JSON object.

    JSON object is of the form:
    { key: value },
    where value can represent any JSON object.

    """
    try:
        value_json = json.loads(value)
    except ValueError:
        # try putting the value into a string
        value_json = json.loads('"{}"'.format(value))
    return json.dumps({key: value_json})


def save_file(key, file_name, *refs):
    """Convert the given parameters to a special JSON object.

    JSON object is of the form:
    { key: {"file": file_name}}, or
    { key: {"file": file_name, "refs": [refs[0], refs[1], ... ]}} if refs are
    given.

    """
    result = {key: {"file": file_name}}
    if refs:
        result[key]["refs"] = refs
    return json.dumps(result)
