import itertools
import json
import re

from os.path import abspath, dirname, join

import click


def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split("([0-9]+)", key)]
    return sorted(l, key=alphanum_key)


def flatmap(func, items):
    return itertools.chain.from_iterable(map(func, items))


def ascii_encode(non_compatible_string):
    """Primarily used for ensuring terminal display compatibility"""
    if non_compatible_string:
        return non_compatible_string.encode("ascii", errors="ignore").decode("ascii")
    else:
        return ""


def pull(nested_dict):
    if "type" in nested_dict and "inputs" not in nested_dict:
        return nested_dict
    else:
        inputs = {}
        if "type" in nested_dict and "inputs" in nested_dict:
            for param, input in list(nested_dict["inputs"].items()):
                inputs[str(param)] = pull(input)
            return inputs
        else:
            return nested_dict


def regex_manifest(protocol, input):
    """Special input types, gets updated as more input types are added"""
    if "type" in input and input["type"] == "choice":
        if "options" in input:
            pattern = "\[(.*?)\]"
            match = re.search(pattern, str(input["options"]))
            if not match:
                click.echo(
                    'Error in %s: input type "choice" options must '
                    'be in the form of: \n[\n  {\n  "value": '
                    '<choice value>, \n  "label": <choice label>\n  '
                    "},\n  ...\n]" % protocol["name"]
                )
                raise RuntimeError
        else:
            click.echo(
                f"Must have options for 'choice' input type. Error in: {protocol['name']}"
            )
            raise RuntimeError


def iter_json(manifest):
    all_types = {}
    try:
        protocol = manifest["protocols"]
    except TypeError:
        raise RuntimeError(
            "Error: Your manifest.json file doesn't contain "
            "valid JSON and cannot be formatted."
        )
    for protocol in manifest["protocols"]:
        types = {}
        for param, input in list(protocol["inputs"].items()):
            types[param] = pull(input)
            if isinstance(input, dict):
                if input["type"] == "group" or input["type"] == "group+":
                    for i, j in list(input.items()):
                        if isinstance(j, dict):
                            for k, l in list(j.items()):
                                regex_manifest(protocol, l)
                else:
                    regex_manifest(protocol, input)
        all_types[protocol["name"]] = types
    return all_types


def by_well(datasets, well):
    return [
        datasets[reading].props["data"][well][0] for reading in list(datasets.keys())
    ]


def makedirs(name, mode=None, exist_ok=False):
    """Forward ports `exist_ok` flag for Py2 makedirs. Retains mode defaults"""
    from os import makedirs

    mode = mode if mode is not None else 0o777
    makedirs(name, mode, exist_ok)


def is_valid_jwt_token(token: str):
    regex = r"Bearer ([a-zA-Z0-9_=]+)\.([a-zA-Z0-9_=]+)\.([a-zA-Z0-9_\-\+\/=]*)"
    return re.fullmatch(regex, token) is not None


def load_sampledata_json(filename: str) -> dict:
    with open(sampledata_path(filename)) as fh:
        return json.load(fh)


def sampledata_path(filename: str) -> str:
    return join(sampledata_dir(), filename)


def sampledata_dir() -> str:
    return abspath(join(dirname(__file__), "sampledata", "_data"))
