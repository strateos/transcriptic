from collections import defaultdict
from transcriptic import Connection

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

    def __init__(self, api, quick_launch_params):
        """
        Initialize TestParameter by providing a web generated params dict.

        Parameters
        ----------
        quick_launch_params: dict
            web browser generated inputs for quick launch
        """
        self.api = api
        self.container_cache = {}
        self.selected_samples = {}
        self.quick_launch_params = quick_launch_params
        self.preview = self.build_preview()

    def build_preview(self):
        """Builds preview parameters"""
        self.modified_params = self.modify_preview_parameters()
        self.refs = self.generate_refs()
        preview = defaultdict(dict)
        preview['preview'].update(self.modified_params)
        preview['preview'].update(self.refs)
        return preview

    def modify_preview_parameters(self):
        """
        This method will traverse the quick launch 'raw_inputs' and modify
        container ids and aliquot dicts into a preview parameter container
        string for autoprotocol generation debugging.
        """
        return self.traverse(
            obj=self.quick_launch_params, callback=self.create_preview_string
        )

    def generate_refs(self):
        """
        This method takes the aggregated containers and aliquots to produce
        the refs aliquot values
        """
        ref_dict = defaultdict(dict)
        for cid, index_arr in self.selected_samples.items():
            container = self.container_cache.get(cid)
            cont_name = PreviewParameters.format_container_name(container)
            ref_dict['refs'][cont_name] = {
                'label': cont_name,
                'type': container.get('container_type').get('id'),
                'store': container.get('storage_condition'),
                'cover': container.get('cover', None),
                'properties': container.get('properties'),
                'aliquots': self.get_selected_aliquots(container, index_arr)
            }
        return ref_dict

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
        return '{}/{}'.format(cont_name, well_idx)

    def create_preview_string(self, value):
        """Creates preview parameters string representation"""
        if isinstance(value, str):
            if value[:2] == 'ct':
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
        container_aliquots = container.get('aliquots')
        for i in index_arr:
            ali = container_aliquots[-int(i)]
            ref_aliquots[i] = {
                'name': ali.get('name'),
                'volume': '{}:microliter'.format(ali.get('volume_ul')),
                'properties': ali.get('properties')
            }
        return ref_aliquots

    @classmethod
    def format_container_name(cls, container):
        return container.get('label').replace(' ', '_')
