import itertools
import json
import re

from collections import OrderedDict, defaultdict
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
            pattern = r"\[(.*?)\]"
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


class PreviewParameters:
    """
    A PreviewParameters object modifies web browser quick launch parameters and
    modifies them for application protocol testing and debugging.

    Attributes
    ------
    api : object
        the Connection object to provide session for using api endpoints

    quick_launch_params: dict
        web browser generated inputs for quick launch

    selected_samples: defaultdict
        all aliquots selected through the web quick launch manifest

    modified_params: dict
        the modified quick launch launch parameters, converts quick launch
        aliquot objects into strings for debugging

    refs: dict
        all unique refs seen in the quick launch parameters

    preview: dict
        the combination of refs and modified_params for scientific
        application debugging

    protocol_obj: dict
        the protocol object from the manifest

    """

    def __init__(self, api, quick_launch_params, protocol_obj):
        """
        Initialize TestParameter by providing a web generated params dict.

        Parameters
        ----------
        quick_launch_params: dict
            web browser generated inputs for quick launch
        """
        self.api = api
        self.protocol_obj = protocol_obj
        self.container_cache = {}
        self.selected_samples = {}
        self.csv_templates = {}
        self.quick_launch_params = quick_launch_params
        self.preview = self.build_preview()

    def build_preview(self):
        """Builds preview parameters"""
        self.modify_preview_parameters()
        self.refs = self.generate_refs()
        preview = defaultdict(lambda: defaultdict(dict))
        preview["preview"]["parameters"].update(self.modified_params)
        preview["preview"].update(self.refs)
        return preview

    def adjust_csv_table_input_type(self):
        """
        Traverses the protocol object from the manifest to find any csv-table
        input types. If it finds one it creates the headers and modifies the
        modified_params that eventually will be the preview parameters for
        autoprotocol testing.
        """
        self.traverse_protocol_obj(self.protocol_obj["inputs"])

    def modify_preview_parameters(self):
        """
        This method will traverse the quick launch 'raw_inputs' and modify
        container ids and aliquot dicts into a preview parameter container
        string for autoprotocol generation debugging.
        """
        self.modified_params = self.traverse_quick_launch(
            obj=self.quick_launch_params, callback=self.create_preview_string
        )
        self.adjust_csv_table_input_type()

    def generate_refs(self):
        """
        This method takes the aggregated containers and aliquots to produce
        the refs aliquot values
        """
        ref_dict = defaultdict(lambda: defaultdict(dict))
        ref_dict["refs"] = {}
        for cid, index_arr in self.selected_samples.items():
            container = self.container_cache.get(cid)
            cont_name = PreviewParameters.format_container_name(container)
            ref_dict["refs"][cont_name] = {
                "label": cont_name,
                "type": container.get("container_type").get("id"),
                "store": container.get("storage_condition"),
                "cover": container.get("cover", None),
                "properties": container.get("properties"),
                "aliquots": {},
            }

            if None not in index_arr:
                ref_dict["refs"][cont_name]["aliquots"] = self.get_selected_aliquots(
                    container, index_arr
                )
            elif container.get("aliquots", None):
                for ali in container.get("aliquots"):
                    ref_dict["refs"][cont_name]["aliquots"][ali["well_idx"]] = {
                        "name": ali["name"],
                        "volume": ali["volume_ul"] + ":microliter",
                        "properties": ali["properties"],
                    }

        return ref_dict

    def traverse_quick_launch(self, obj, callback=None):
        """
        Will traverse quick launch object and send value to a callback
        action method.
        """
        if isinstance(obj, dict):
            # If object has 'containerId' and 'wellIndex', then it is an aliquot
            if "containerId" and "wellIndex" in obj.keys():
                return self.create_string_from_aliquot(value=obj)
            else:
                value = {
                    k: self.traverse_quick_launch(v, callback) for k, v in obj.items()
                }
        elif isinstance(obj, list):
            return [self.traverse_quick_launch(elem, callback) for elem in obj]
        else:
            value = obj

        if callback is None:
            return value
        else:
            return callback(value)

    def add_to_cache(self, container_id):
        """Adds requested container to cache for later use"""
        if container_id in self.container_cache:
            container = self.container_cache[container_id]
        else:
            container = self.api.get_container(container_id)
            self.container_cache[container_id] = container
        return container

    def create_string_from_aliquot(self, value):
        """Creates preview aliquot representation"""
        well_idx = value.get("wellIndex")
        container_id = value.get("containerId")
        container = self.add_to_cache(container_id)
        cont_name = PreviewParameters.format_container_name(container)
        self.add_to_selected(container_id, well_idx)
        return "{}/{}".format(cont_name, well_idx)

    def create_preview_string(self, value):
        """Creates preview parameters string representation"""
        if isinstance(value, str):
            if value[:2] == "ct":
                container_id = value
                container = self.add_to_cache(container_id)
                cont_name = PreviewParameters.format_container_name(container)
                self.add_to_selected(container_id)
                return cont_name
            else:
                return value
        else:
            return value

    def add_to_selected(self, container_id, well_idx=None):
        """Saves which containers were selected."""
        if container_id in self.selected_samples:
            self.selected_samples[container_id].append(well_idx)
        else:
            self.selected_samples[container_id] = [well_idx]

    def get_selected_aliquots(self, container, index_arr):
        """Grabs the properties from the selected aliquots"""
        ref_aliquots = dict()
        container_aliquots = {
            ali.get("well_idx"): ali for ali in container.get("aliquots")
        }
        for i in index_arr:
            ali = container_aliquots.get(i, container)
            ref_aliquots[i] = {
                "name": ali.get("name"),
                "volume": "{}:microliter".format(ali.get("volume_ul", 10)),
                "properties": ali.get("properties"),
            }
        return ref_aliquots

    def update_nested(self, in_dict, key, value):
        for k, v in in_dict.items():
            if key == k:
                in_dict[k] = [value, v]
            elif isinstance(v, dict):
                self.update_nested(v, key, value)
            elif isinstance(v, list):
                for o in v:
                    if isinstance(o, dict):
                        self.update_nested(o, key, value)

    def traverse_protocol_obj(self, obj, parentkey=None):
        if isinstance(obj, dict):
            if obj.get("type") == "csv-table":
                t = obj.get("template")
                headers = {k: c for k, c in zip(t.get("keys"), t.get("col_type"))}
                self.update_nested(self.modified_params, parentkey, headers)
                return obj
            else:
                value = {
                    pkey: self.traverse_protocol_obj(v, pkey) for pkey, v in obj.items()
                }
        elif isinstance(obj, list):
            return [self.traverse_protocol_obj(elem, parentkey) for elem in obj]
        else:
            value = obj
        return value

    def merge(self, manifest):
        # Get selected protocol
        selected_protocol = next(
            p
            for p in manifest["protocols"]
            if p["name"] == self.protocol_obj.get("name")
        )

        # Get the index of the protocol in the protocols list
        protocol_idx = manifest["protocols"].index(selected_protocol)
        updated_protocol = OrderedDict()
        # Ensure that the merged protocol object has the same key order
        updated_protocol["name"] = self.protocol_obj["name"]
        updated_protocol["display_name"] = self.protocol_obj["display_name"]
        updated_protocol["categories"] = self.protocol_obj.get("categories", [])
        updated_protocol["description"] = self.protocol_obj["description"]
        updated_protocol["version"] = self.protocol_obj["version"]
        updated_protocol["command_string"] = self.protocol_obj["command_string"]
        updated_protocol["inputs"] = self.protocol_obj["inputs"]
        updated_protocol["preview"] = self.preview.get("preview")

        # Place modified protocol in the appropriate index
        manifest["protocols"][protocol_idx] = updated_protocol

        # Ensure that manifest has correct order
        self.merged_manifest = OrderedDict()
        self.merged_manifest["format"] = "python"
        self.merged_manifest["license"] = "MIT"
        self.merged_manifest["protocols"] = manifest["protocols"]

    @classmethod
    def format_container_name(cls, container):
        return container.get("label").replace(" ", "_")
