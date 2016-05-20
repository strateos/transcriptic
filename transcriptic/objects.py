from __future__ import print_function
from __future__ import absolute_import
from builtins import str
import pandas as pd
from builtins import object
import warnings

def _check_api(obj_type):
    from transcriptic import api
    if not api:
        raise RuntimeError("You have to be logged in to be able to create %s objects" % obj_type)
    return api


class ProtocolPreview(object):
    def __init__(self, protocol, connection):
        self.protocol = protocol
        self.preview_url = connection.preview_protocol(protocol)

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
        style="height:500px" seamless></iframe>""" % self.preview_url


class _BaseObject(object):
    """Base object which other objects inherit from"""
    # TODO: Inherit more stuff from here. Need to ensure web has unified fields for objects
    def __init__(self, obj_type, obj_id, attributes, connection=None):
        # If attributes and connection are explicitly provided, just return and not do any smart parsing
        if attributes and connection:
            self.connection = connection
            self.attributes = attributes
        else:
            if not connection:
                self.connection = _check_api(obj_type)
            else:
                self.connection = connection
            (self.id, self.name) = self.load_object(obj_type, obj_id)
            if not attributes:
                self.attributes = self.connection._get_object(self.id)
            else:
                self.attributes = attributes

    def load_object(self, obj_type, obj_id):
        """Find and match object by name"""
        #TODO: Remove the try/except statement and properly handle cases where objects are not found
        try:
            objects = getattr(self.connection, obj_type + 's')()
        except:
            return (obj_id, str(obj_id))
        matched_objects = []
        for obj in objects:
            # Special case here since we use both 'name' and 'title' for object names
            if 'name' in obj:
                if obj_id == obj['name'] or obj_id == obj['id']:
                    matched_objects.append((obj['id'], obj['name']))
            if 'title' in obj:
                if obj_id == obj['title'] or obj_id == obj['id']:
                    matched_objects.append((obj['id'], obj['title']))
        if len(matched_objects) == 0:
            raise TypeError("%s is not found in your %ss." % (obj_id, obj_type))
        elif len(matched_objects) == 1:
            return matched_objects[0]
        else:
            print ("More than 1 match found. Defaulting to the first match: %s" % (matched_objects[0]))
            return matched_objects[0]


class Project(_BaseObject):
    """
    A Project object contains helper methods for managing your runs. You can view the runs associated with this project
    as well as submit runs to the project.

    Example Usage:

    .. code-block:: python

        myProject = Project("My Project")
        projectRuns = myProject.runs()
        myRunId = projectRuns.query("title == 'myRun'").id.item()
        myRun = Run(myRunId)

    Attributes
    ----------
    id : str
        Project id
    name: str
        Project name
    attributes: dict
        Master attributes dictionary
    connection: transcriptic.config.Connection
        Transcriptic Connection object associated with this specific object

    """
    def __init__(self, project_id, attributes=None, connection=None):
        """
        Initialize a Project by providing a project name/id. The attributes and connection parameters are generally
        not specified unless one wants to manually initialize the object.

        Parameters
        ----------
        project_id: str
            Project name or id in string form
        attributes: Optional[dict]
            Attributes of the project
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless explicitly provided
        """
        super(Project, self).__init__('project', project_id, attributes, connection)
        self._runs = pd.DataFrame()

    def runs(self, use_cache=True):
        """
        Get the list of runs belonging to the project

        Parameters
        ----------
        use_cache: Boolean
            Determines whether the cached list of runs is returned

        Returns
        -------
        DataFrame
            Returns a DataFrame of runs, with the id and title as columns
        """
        if self._runs.empty and use_cache:
            temp = self.connection.env_args
            self.connection.update_environment(project_id=self.id)
            project_runs = self.connection.runs()
            self._runs = pd.DataFrame([[pr['id'], pr['title']] for pr in project_runs])
            self._runs.columns = ['id', 'Name']
            self.connection.env_args = temp
        return self._runs

    def submit(self, protocol, title, test_mode=False):
        """
        Submit a run to this project

        Parameters
        ----------
        protocol: dict
            Autoprotocol Protocol in dictionary form, can be generated using Protocol.as_dict()
        title: Optional[str]
            Title of run. Run-id will automatically be used as name if field is not provided
        test_mode: Optional[boolean]
            Determines if run will be submitted will be treated as a test run or a run that is meant for execution

        Returns
        -------
        Run
            Returns a run object if run is successfully submitted
        """
        response = self.connection.submit_run(protocol, project_id=self.id, title=title, test_mode=test_mode)
        return Run(response['id'], response)


class Run(_BaseObject):
    """
    A Run object contains helper methods for accessing Run-related information such as Instructions, Datasets
    and monitoring data

    Example Usage:

        .. code-block:: python

        myRun = Run('r12345')
        myRun.data
        myRun.instructions

    Attributes
    ----------
    id : str
        Run id
    name: str
        Run name
    data: DataFrame
        DataFrame of all datasets which belong to this run
    instructions: DataFrame
        DataFrame of all Instruction objects which belong to this run
    project_id : str
        Project id which run belongs to
    attributes: dict
        Master attributes dictionary
    connection: transcriptic.config.Connection
        Transcriptic Connection object associated with this specific object

    """
    def __init__(self, run_id, attributes=None, connection=None):
        """
        Initialize a Run by providing a run name/id. The attributes and connection parameters are generally
        not specified unless one wants to manually initialize the object.

        Parameters
        ----------
        run_id: str
            Run name or id in string form
        attributes: Optional[dict]
            Attributes of the run
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless explicitly provided
        """
        super(Run, self).__init__('run', run_id, attributes, connection)
        self.project_id = self.attributes['project']['url']
        self._instructions = pd.DataFrame()
        self._data = pd.DataFrame()

    @property
    def instructions(self):
        if self._instructions.empty:
            instruction_list = [Instruction(dict(x, **{'project_id': self.project_id, 'run_id': self.id}),
                                              connection=self.connection)
                                  for x in self.attributes["instructions"]]
            self._instructions = pd.DataFrame(instruction_list)
            self._instructions.columns = ["Instructions"]
            self._instructions.insert(0, "Name", [inst.name for inst in self._instructions.Instructions])
            self._instructions.insert(1, "Started", [inst.started_at for inst in self._instructions.Instructions])
            self._instructions.insert(2, "Completed", [inst.completed_at for inst in self._instructions.Instructions])
        return self._instructions

    @property
    def data(self):
        """
        Find and generate a list of Dataset objects which are associated with this run

        Returns
        -------
        DataFrame
            Returns a DataFrame of datasets, with Name, Dataset and DataType as columns

        """
        if self._data.empty:
            datasets = self.connection.datasets(project_id=self.project_id, run_id=self.id)
            data_dict = {k: Dataset(datasets[k]["id"], dict(datasets[k], title=k),
                                    connection=self.connection)
                         for k in list(datasets.keys()) if datasets[k]}
            self._data = pd.DataFrame(sorted(list(data_dict.items()), key=lambda x: x[0]))
            self._data.columns = ["Name", "Datasets"]
            self._data.insert(1, "DataType", ([ds.operation for ds in self._data.Datasets]))
        return self._data

    def monitoring(self, instruction_id, data_type='pressure'):
        """
        View monitoring data of a given instruction

        Parameters
        ----------
        instruction_id: str
            Instruction id in string form
        data_type: str
            Monitoring data type, defaults to 'pressure'

        Returns
        -------
        DataFrame
            Returns a pandas dataframe of the monitoring data
        """
        response = self.connection.monitoring_data(
            project_id=self.project_id,
            run_id=self.id,
            instruction_id=instruction_id,
            data_type=data_type
        )
        return pd.DataFrame(response['results'])

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
        style="height:450px" seamless></iframe>""" % \
               self.connection.get_route('view_run', project_id=self.project_id, run_id=self.id)


class Dataset(_BaseObject):
    """
    A Dataset object contains helper methods for accessing data related information

    Attributes
    ----------
    id : str
        Dataset id
    name: str
        Dataset name
    data : DataFrame
        DataFrame of well-indexed data values. Note that associated metadata is found in attributes dictionary
    container: Container
        Container object that was used for this dataset
    operation: str
        Operation used for generating the dataset
    data_type: str
        Data type of this dataset
    attributes: dict
        Master attributes dictionary
    connection: transcriptic.config.Connection
        Transcriptic Connection object associated with this specific object

    """
    def __init__(self, data_id, attributes=None, connection=None):
        """
        Initialize a Dataset by providing a data name/id. The attributes and connection parameters are generally
        not specified unless one wants to manually initialize the object.

        Parameters
        ----------
        data_id: str
            Dataset name or id in string form
        attributes: Optional[dict]
            Attributes of the dataset
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless explicitly provided
        """
        super(Dataset, self).__init__('dataset', data_id, attributes, connection)
        # TODO: Get BaseObject to handle dataset name
        self.name = self.attributes["title"]
        self.id = data_id
        self.operation = self.attributes["instruction"]["operation"]["op"]
        self.data_type = self.attributes["data_type"]
        self._data = pd.DataFrame()
        self.container = Container(self.attributes["container"]["id"], attributes=self.attributes["container"],
                                   connection=connection)

    @property
    def data(self, key="*"):
        if self._data.empty:
            # Get all data initially (think about lazy loading in the future)
            self._data = pd.DataFrame(self.connection.dataset(data_id=self.id, key="*"))
            self._data.columns = [x.upper() for x in self._data.columns]
        if key == "*":
            return self._data
        else:
            return self._data[key]

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
            style="height:500px" seamless></iframe>""" % \
               self.connection.get_route('view_data', data_id=self.id)


class Instruction(object):
    """
    An Instruction object contains information related to the current instruction such as the start,
    completed time as well as warps associated with the instruction.
    Note that Instruction objects are usually created as part of a run and not created explicity.

    Additionally, if diagnostic information is available, one can click on the `Show Diagnostics Data`
    button to view relevant diagnostic information.

    Example Usage:

        .. code-block:: python

        myRun = Run('r12345')
        myRun.instructions

        # Access instruction object
        myRun.instructions.Instructions[1]
        myRun.instructions.Instructions[1].warps


    Attributes
    ----------
    id : str
        Instruction id
    name: str
        Instruction name
    warps : DataFrame
        DataFrame of warps in the instruction
    started_at : str
        Time where instruction begun
    completed_at : str
        Time where instruction ended
    device_id: str
        Id of device which instruction was executed on
    attributes: dict
        Master attributes dictionary
    connection: transcriptic.config.Connection
        Transcriptic Connection object associated with this specific object
    """

    def __init__(self, attributes, connection=None):
        """
        Parameters
        ----------
        attributes : dict
            Instruction attributes
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless explicitly provided
        """
        self.connection = connection
        self.attributes = attributes
        self.id = attributes["id"]
        self.name = attributes["operation"]["op"]
        self.started_at = attributes["started_at"]
        self.completed_at = attributes["completed_at"]
        if len(attributes["warps"]) > 0:
            device_id_set = set([warp["device_id"] for warp in self.attributes["warps"]])
            self.device_id = device_id_set.pop()
            if len(device_id_set) > 1:
                warnings.warn("There is more than one device involved in this instruction. Please contact "
                              "Transcriptic for assistance.")

        else:
            self.device_id = None
        self._warps = pd.DataFrame()

    @property
    def warps(self):
        if self._warps.empty:
            warp_list = self.attributes["warps"]
            self._warps = pd.DataFrame(x['command'] for x in warp_list)
            self._warps.columns = [x.title() for x in self._warps.columns.tolist()]
            self._warps.insert(1, "Started", [x["reported_started_at"] for x in warp_list])
            self._warps.insert(2, "Completed", [x["reported_completed_at"] for x in warp_list])
        return self._warps

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
            style="height:1000px" seamless></iframe>""" % \
               self.connection.get_route('view_instruction', run_id= self.attributes["run_id"],
                                         project_id= self.attributes["project_id"], instruction_id=self.id)


class Container(_BaseObject):
    """
    A Container object represents a container from the Transcriptic LIMS and
    contains relevant information on the container type as well as the
    aliquots present in the container.

    Example Usage:
        .. code-block:: python

          my_container = container("ct186apgz6a374")
          my_container.well_map
          my_container.aliquots

          my_container.container_type.col_count
          my_container.container_type.robotize("B1")
          my_container.container_type.humanize(12)

    Attributes
    ----------
    name: str
        Name of container
    well_map: dict
        Well mapping with well indices for keys and well names as values
    aliquots: DataFrame
        DataFrame of aliquots present in the container
    container_type: autoprotocol.container_type.ContainerType
        Autoprotocol ContainerType object with many useful container type
        information and functions.

        Example Usage:

        .. code-block:: python

          my_container = container("ct186apgz6a374")

          my_container.well_map

          my_container.container_type.col_count
          my_container.container_type.robotize("B1")
          my_container.container_type.humanize(12)


    """

    def __init__(self, container_id, attributes=None, connection=None):
        """
        Initialize a Container by providing a container name/id. The attributes and connection parameters are generally
        not specified unless one wants to manually initialize the object.

        Parameters
        ----------
        container_id: str
            Container name or id in string form
        attributes: Optional[dict]
            Attributes of the container
        connection: Optional[transcriptic.config.Connection]
            Connection context. The default context object will be used unless explicitly provided
        """
        super(Container, self).__init__('container', container_id, attributes, connection)
        # TODO: Unify container "label" with name, add Containers route
        self.id = container_id
        self.name = self.attributes["label"]
        self.well_map = {aliquot["well_idx"]: aliquot["name"]
                        for aliquot in attributes["aliquots"]}
        self.container_type = self._parse_container_type()
        self._aliquots = pd.DataFrame()

    def _parse_container_type(self):
        """Helper function for parsing container string into container object"""
        from autoprotocol.container_type import _CONTAINER_TYPES
        from autoprotocol.container_type import ContainerType
        from copy import deepcopy
        container_type = deepcopy(self.attributes["container_type"])

        container_type.pop("well_type", None)
        container_type.pop("id", None)
        if "dead_volume" not in container_type:
            container_type["dead_volume_ul"] = _CONTAINER_TYPES[
                container_type["shortname"]].dead_volume_ul
        if "safe_min_volume_ul" not in container_type:
            container_type["safe_min_volume_ul"] = _CONTAINER_TYPES[
                container_type["shortname"]].safe_min_volume_ul

        return ContainerType(**container_type)

    @property
    def aliquots(self):
        if self._aliquots.empty:
            aliquot_list = self.attributes["aliquots"]
            self._aliquots = pd.DataFrame([dict({'Name': x['name'], 'Id': x['id'],
                                            'Volume': x['volume_ul']}, **x['properties'])
                                           for x in aliquot_list])
        return self._aliquots


def __repr__(self):
        """
        Return a string representation of a Container using the specified name.
        (ex. Container('my_plate'))

        """
        return "Container(%s)" % (str(self.name))
