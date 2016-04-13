from builtins import object
import json
import pandas
from autoprotocol import Protocol


class ProtocolPreview(object):

    def __init__(self, protocol, connection):
        self.protocol = protocol
        self.preview_url = connection.preview_protocol(protocol)

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
        style="height:500px;" seamless></iframe>""" % self.preview_url


class Instructions(object):

    """
    An instruction object contains raw instructions as JSON as well as list of
    operations and warps generated from the raw instructions.

    Parameters
    ----------

    raw_instructions : dict
      raw instruction dictionary

    """

    def __init__(self, raw_instructions):
        self.raw_instructions = raw_instructions
        op_name_list = []
        op_warp_list = []
        for instruction in raw_instructions:
            op_name_list.append(instruction["operation"]["op"])
            op_warp_list.append(instruction["warps"])
        instruct_dict = {}
        instruct_dict["name"] = op_name_list
        instruct_dict["warp_list"] = op_warp_list
        self.df = pandas.DataFrame(instruct_dict)


class Dataset(object):

    def __init__(self, obj_id, attributes, connection=False):
        super(Dataset, self).__init__()
        self.id = obj_id
        self.attributes = attributes
        self.connection = connection
        # self.df = pandas.DataFrame(attributes)

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
        style="height:500px;" seamless></iframe>""" % \
            self.connection.get_route('view_data', data_id=self.id)


class Run(object):

    def __init__(self, obj_id, attributes, connection=False):
        super(Run, self).__init__()
        self.id = obj_id
        self.attributes = attributes
        self.instructions = Instructions(self.attributes["instructions"])
        self.connection = connection

    def monitoring(self, instruction_id, data_type='pressure'):
        req = self.connection.monitoring_data(
            project_id=self.attributes['project']['url'],
            run_id=self.id,
            instruction_id=instruction_id,
            data_type=data_type
        )
        if req.status_code == 200:
            response = req.json()
            return pandas.DataFrame(response['results'])
        else:
            raise Exception(req.text)

    def data(self):
        datasets = self.connection.datasets(project_id=self.attributes['project']['url'], run_id=self.id)
        return {k: Dataset(datasets[k]["id"], datasets[k],
                           connection=self.connection)
                for k in list(datasets.keys()) if datasets[k]}

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
        style="height:450px;" seamless></iframe>""" % \
            self.connection.get_route('view_run', project_id=self.attributes['project']['url'], run_id=self.id)


class Project(object):

    def __init__(self, obj_id, attributes, connection=False):
        super(Project, self).__init__()
        self.id = obj_id
        self.attributes = attributes
        self.connection = connection

    def runs(self):
        runs = self.connection.runs(project_id=self.id)
        return [Run(run['id'], run, self.connection) for run in runs]

    def submit(self, protocol, title, test_mode=False):
        response = self.connection.submit_run(protocol,project_id= self.id, title=title, test_mode=test_mode)
        return Run(response['id'], response)


class Aliquot(object):

    def __init__(self, obj_id, attributes, connection=False):
        super(Aliquot, self).__init__()
        self.id = obj_id
        self.attributes = attributes
        self.connection = connection


class Container(object):

    """
    A Container object represents a container from the Transcriptic LIMS and
    contains relevant information on the container type as well as the
    aliquots present in the container.

    Parameters
    ----------

    name: str
        Name of container
    wellMap: dict
        Well mapping with well indices for keys and well names as values
    aliquots: list
        List of aliquots present in the container
    containerType: autoprotocol.container_type.ContainerType
        Autoprotocol ContainerType object with many useful container type
        information and functions.

        Example Usage:

        .. code-block:: python

          my_container = container("ct186apgz6a374")

          my_container.wellMap

          my_container.containerType.col_count
          my_container.containerType.robotize("B1")
          my_container.containerType.humanize(12)

    """

    def __init__(self, obj_id, attributes, connection=False):
        super(Container, self).__init__()
        self.id = obj_id
        self.attributes = attributes
        self.connection = connection

        self.name = self.attributes["label"]
        self.aliquots = self.attributes["aliquots"]
        self.wellMap = {aliquot["well_idx"]: aliquot["name"]
                        for aliquot in self.aliquots}

        def parse_containerType():
            from autoprotocol.container_type import _CONTAINER_TYPES
            from autoprotocol.container_type import ContainerType
            from copy import deepcopy
            containerType = deepcopy(self.attributes["container_type"])

            containerType.pop("well_type", None)
            containerType.pop("id", None)
            if "dead_volume" not in containerType:
                containerType["dead_volume_ul"] = _CONTAINER_TYPES[
                    containerType["shortname"]].dead_volume_ul
            if "safe_min_volume_ul" not in containerType:
                containerType["safe_min_volume_ul"] = _CONTAINER_TYPES[
                    containerType["shortname"]].safe_min_volume_ul

            return ContainerType(**containerType)
        self.containerType = parse_containerType()

    def __repr__(self):
        """
        Return a string representation of a Container using the specified name.
        (ex. Container('my_plate'))

        """
        return "Container(%s)" % (str(self.name))


class Resource(object):

    def __init__(self, obj_id, attributes, connection=False):
        super(Resource, self).__init__()
        self.id = obj_id
        self.attributes = attributes
        self.connection = connection
