from collections import defaultdict
from transcriptic.jupyter.objects import Container


class PreviewParameters:
    """
    A PreviewParameters object modifies web browser quick launch parameters and
    modifies them for application protocol testing and debugging.

    Attributes
    ------
    params: dict
        web browser generated inputs for quick launch

    selected_aliquots: defaultdict
        all aliquots selected through the web quick launch manifest

    modified_params: dict
        the modified quick launch launch parameters, converts quick launch
        aliquot objects into strings for debugging

    refs: dict
        all unique refs seen in the quick launch parameters

    preview: dict
        the combination of refs and modified_params for scientific
        application debugging
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
        self.selected_aliquots = []  # defaultdict(list)
        self.modified_params = self.modify_preview_parameters()
        self.refs = self.generate_refs()
        self.preview = self.build_preview()

    def modify_preview_parameters(self):
        """
        This method will traverse the quick launch 'raw_inputs' and modify
        container ids and aliquot dicts into a preview parameter container
        string for autoprotocol generation debugging.
        """
        return self.traverse(self.params, self.create_preview_string)

    def traverse(self, obj, callback=None):
        """
        Will traverse quick launch object and send value to a callback
        action method.
        """
        if isinstance(obj, dict):
            # If object has 'containerId' and 'wellIndex', then it is an aliquot
            if 'containerId' and 'wellIndex' in obj.keys():
                return self.create_string_from_aliquot(value=obj)
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

    def create_string_from_aliquot(self, value):
        """Creates preview aliquot representation"""
        container_id = value.get("containerId", None)
        well_idx = value.get("wellIndex", None)
        container = Container(container_id)
        cont_name = container.name.replace(' ', '_')
        self.selected_aliquots.append((container, well_idx))
        return '{}/{}'.format(cont_name, well_idx)

    def create_preview_string(self, value):
        """Creates preview parameters string reprsentation"""
        if isinstance(value, str):
            if value[:2] == 'ct':
                container_id = value
                container = Container(container_id)
                cont_name = container.name.replace(' ', '_')
                self.selected_aliquots.append((container, None))
                return cont_name
            else:
                return value
        else:
            return value

    def generate_refs(self):
        """
        This method takes the aggregated containers and aliquots to produce
        the refs aliquot values
        """
        ref_dict = dict()
        for container, idx in self.selected_aliquots:
            cont_name = container.name.replace(' ', '_')
            ref_dict[cont_name] = {
                'label': container.name,
                'type': container.attributes['container_type_id'],
                'store': container.storage,
                'seal': container.cover,
                'aliquots': PreviewParameters.container_aliquots(container)
            }
        return {'refs': ref_dict}

    def build_preview(self):
        preview = {'preview': dict()}
        preview['preview'].update(self.refs)
        preview['preview'].update(self.modified_params)
        return preview

    @classmethod
    def container_aliquots(cls, container):
        ref_aliquots = dict()
        for ali in container.attributes['aliquots']:
            ref_aliquots[ali['well_idx']] = {
                'name': ali['name'],
                'properties': ali['properties'],
                'volume': '{}:microliter'.format(ali['volume_ul'])
            }
        return ref_aliquots
