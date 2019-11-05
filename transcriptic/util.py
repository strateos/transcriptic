import click
import itertools
import re
import sys
from collections import defaultdict
from transcriptic.jupyter.objects import Container


def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)


def flatmap(func, items):
    return itertools.chain.from_iterable(map(func, items))


def ascii_encode(non_compatible_string):
    """Primarily used for ensuring terminal display compatibility"""
    if non_compatible_string:
        return non_compatible_string.encode('ascii', errors='ignore').decode("ascii")
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
            pattern = '\[(.*?)\]'
            match = re.search(pattern, str(input["options"]))
            if not match:
                click.echo("Error in %s: input type \"choice\" options must "
                           "be in the form of: \n[\n  {\n  \"value\": "
                           "<choice value>, \n  \"label\": <choice label>\n  "
                           "},\n  ...\n]" % protocol['name'])
                raise RuntimeError
        else:
            click.echo("Must have options for 'choice' input type." +
                       " Error in: " + protocol["name"])
            raise RuntimeError


def iter_json(manifest):
    all_types = {}
    try:
        protocol = manifest['protocols']
    except TypeError:
        raise RuntimeError("Error: Your manifest.json file doesn't contain "
                           "valid JSON and cannot be formatted.")
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


def robotize(well_ref, well_count, col_count):
    """Function referenced from autoprotocol.container_type.robotize()"""
    if isinstance(well_ref, list):
        return [robotize(well, well_count, col_count) for well in well_ref]
    if not isinstance(well_ref, (str, int)):
        raise TypeError("ContainerType.robotize(): Well reference given "
                        "is not of type 'str' or 'int'.")

    well_ref = str(well_ref)
    m = re.match("([a-z])(\d+)$", well_ref, re.I)
    if m:
        row = ord(m.group(1).upper()) - ord('A')
        col = int(m.group(2)) - 1
        well_num = row * col_count + col
        # Check bounds
        if row > (well_count // col_count):
            raise ValueError("Row given exceeds "
                             "container dimensions.")
        if col > col_count or col < 0:
            raise ValueError("Col given exceeds "
                             "container dimensions.")
        if well_num > well_count:
            raise ValueError("Well given "
                             "exceeds container dimensions.")
        return well_num
    else:
        m = re.match("\d+$", well_ref)
        if m:
            well_num = int(m.group(0))
            # Check bounds
            if well_num > well_count or well_num < 0:
                raise ValueError("Well number "
                                 "given exceeds container dimensions.")
            return well_num
        else:
            raise ValueError("Well must be in "
                             "'A1' format or be an integer.")


def humanize(well_ref, well_count, col_count):
    """Function referenced from autoprotocol.container_type.humanize()"""
    if isinstance(well_ref, list):
        return [humanize(well, well_count, col_count) for well in well_ref]
    if isinstance(well_ref, str):
        try:
            well_ref = int(well_ref)
        except:
            raise ValueError("Well reference (%s) given has to be parseable into int." % well_ref)
    if not isinstance(well_ref, int):
        raise TypeError("Well reference (%s) given "
                        "is not of type 'int'." % well_ref)
    idx = robotize(well_ref, well_count, col_count)
    row, col = (idx // col_count, idx % col_count)
    # Check bounds
    if well_ref > well_count or well_ref < 0:
        raise ValueError("Well reference "
                         "given exceeds container dimensions.")
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[row] + str(col + 1)


def by_well(datasets, well):
    return [datasets[reading].props['data'][well][0] for
            reading in list(datasets.keys())]


def makedirs(name, mode=None, exist_ok=False):
    """Forward ports `exist_ok` flag for Py2 makedirs. Retains mode defaults"""
    from os import makedirs
    mode = mode if mode is not None else 0o777
    makedirs(name, mode, exist_ok)


class TestParameters:
    """
    A TestParameters object modifies web browser quick launch parameters and modifies them for application
    protocol testing and debugging.

    Attributes
    ------
    params: dict
        web browser generated inputs for quick launch

    selected_aliquots: defaultdict
        all aliquots selected through the web quick launch manifest

    modified_params: dict
        the modified quick launch launch parameters, converts quick launch aliquot objects into strings for debugging

    refs: dict
        all unique refs seen in the quick launch parameters

    preview: dict
        the combination of refs and modified_params for scientific application debugging

    """
    def __init__(self, params):
        """
        Initialize TestParameter by providing a web generated params dict.

        Parameters
        ----------
        params: dict
            web browser generated inputs for quick launch
        """
        self.params = params
        self.selected_aliquots = defaultdict(list)
        self.modified_params = self.modify_preview_parameters()
        self.refs = self.generate_refs()
        self.preview = self.build_preview()

    def modify_preview_parameters(self):
        return self.traverse_modify(self.params, self.create_container_string)

    def traverse_modify(self, obj, action):
        return self.traverse(obj, callback=action)

    def traverse(self, obj, callback=None):
        if isinstance(obj, dict):
            if list(obj.keys()) == ['containerId', 'wellIndex']:
                value = obj
            else:
                value = {k: self.traverse(v, callback) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.traverse(elem, callback) for elem in obj]
        else:
            value = obj

        if callback is None:
            return value
        else:
            return callback(value)

    def create_container_string(self, aliquot):
        if isinstance(aliquot, dict):
            container_id = aliquot.get('containerId', None)
        elif isinstance(aliquot, str):
            container_id = None
        else:
            raise ValueError('This {} {} is not supported by this action method'.format(type(aliquot), aliquot))

        if container_id:
            well_idx = aliquot['wellIndex']
            container = Container(container_id)
            self.selected_aliquots[container.id].append(well_idx)
            return '{}/{}'.format(container.name.replace(' ', '_'), well_idx)
        else:
            return aliquot

    def build_preview(self):
        preview = {'preview': dict()}
        preview['preview'].update(self.refs)
        preview['preview'].update(self.modified_params)
        return preview

    def generate_refs(self):
        ref_dict = dict()
        for cid, well_arr in self.selected_aliquots.items():
            container = Container(cid)
            cont_name = container.name.replace(' ', '_')
            ref_aliquots = TestParameters.container_aliquots(container)
            ref_dict[cont_name] = {
                'label': container.name,
                'type': container.attributes['container_type_id'],
                'store': container.storage,
                'seal': container.cover,
                'aliquots': {well_idx: ref_aliquots[well_idx] for well_idx in well_arr}
            }
        return {'refs': ref_dict}

    @classmethod
    def container_aliquots(cls, container):
        ref_aliquots = dict()
        for ali in container.attributes['aliquots']:
            ref_aliquots[ali['well_idx']] = {
                'name': ali['name'],
                'properties': ali['properties'],
                'volume': '0.0:microliters'
            }
        return ref_aliquots
