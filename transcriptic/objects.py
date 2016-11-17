from __future__ import print_function
from __future__ import absolute_import
from operator import itemgetter
from builtins import str
import pandas as pd
from builtins import object
import warnings
from autoprotocol import Unit
from requests.exceptions import ReadTimeout
from copy import deepcopy


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
        # TODO: Remove the try/except statement and properly handle cases where objects are not found
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
            print("More than 1 match found. Defaulting to the first match: %s" % (matched_objects[0]))
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
            myRun.containers
            myRun.Instructions[0]

    Attributes
    ----------
    id : str
        Run id
    name: str
        Run name
    data: DataFrame
        DataFrame summary of all datasets which belong to this run
    instructions: DataFrame
        DataFrame summary of all Instruction objects which belong to this run
    containers: DataFrame
        DataFrame summary of all Container objects which belong to this run
    project_id : str
        Project id which run belongs to
    attributes: dict
        Master attributes dictionary
    connection: transcriptic.config.Connection
        Transcriptic Connection object associated with this specific object

    """

    def __init__(self, run_id, attributes=None, connection=None, timeout=30.0):
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
        timeout: Optional[float]
            Timeout in seconds (defaults to 30.0). This will be used when making API calls to fetch data associated with the run.
        """
        super(Run, self).__init__('run', run_id, attributes, connection)
        self.project_id = self.attributes['project']['id']
        self.timeout = timeout
        self._data_ids = pd.DataFrame()
        self._instructions = pd.DataFrame()
        self._containers = pd.DataFrame()
        self._data = pd.DataFrame()

    @property
    def data_ids(self):
        """
        Find and generate a list of datarefs and data_ids associated with this run.

        Returns
        -------
        DataFrame
            Returns a DataFrame of data ids, with datarefs and data_ids as columns

        """
        if self._data_ids.empty:
            data_dict = {instruction.attributes['operation']['dataref']: instruction.attributes['dataset']['id'] for instruction in self.instructions['Instructions'] if 'dataset' in instruction.attributes}
            if len(data_dict) > 0:
                self._data_ids = pd.DataFrame(sorted(data_dict.items()))
                self._data_ids.columns = ["dataref", "data_id"]
        return self._data_ids

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
    def Instructions(self):
        """
        Helper for allowing direct access of `Instruction` objects

        Returns
        -------
        Series
            Returns a Series of `Instruction` objects

        """
        return self.instructions.Instructions

    @property
    def containers(self):
        if self._containers.empty:
            container_list = []
            for ref in Run(self.id).attributes["refs"]:
                container_list.append(Container(ref["container"]["id"]))
            self._containers = pd.DataFrame(container_list)
            self._containers.columns = ["Containers"]
            self._containers.insert(0, "Name", [container.name for container in self._containers.Containers])
            self._containers.insert(1, "ContainerId", [container.id for container in self._containers.Containers])
            self._containers.insert(2, "Type", [container.container_type.shortname for container in self._containers.Containers])
            self._containers.insert(3, "Status", [container.attributes["status"] for container in self._containers.Containers])
            self._containers.insert(4, "Storage Condition", [container.storage for container in self._containers.Containers])
        return self._containers

    @property
    def Containers(self):
        """
        Helper for allowing direct access of `Container` objects

        Returns
        -------
        Series
            Returns a Series of `Container` objects
        """
        return self.containers.Containers

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
            num_datasets = len(self.data_ids)
            if num_datasets == 0:
                print("No datasets were found.")
            else:
                print("Attempting to fetch %d datasets..." % num_datasets)
                try:
                    datasets = self.connection.datasets(project_id=self.project_id, run_id=self.id, timeout=self.timeout)
                    data_dict = {k: Dataset(datasets[k]["id"], dict(datasets[k], title=k),
                                            connection=self.connection)
                                 for k in list(datasets.keys()) if datasets[k]}
                    self._data = pd.DataFrame(sorted(list(data_dict.items()), key=lambda x: x[0]))
                    self._data.columns = ["Name", "Datasets"]
                    self._data.insert(1, "DataType", ([ds.operation for ds in self._data.Datasets]))
                except ReadTimeout:
                    print('Operation timed out after %d seconds. Returning data_ids instead of Datasets.\nTo try again, increase value of self.timeout and resubmit request.' % self.timeout)
                    return self.data_ids
        return self._data

    @property
    def Datasets(self):
        """
        Helper for allowing direct access of `Dataset` objects

        Returns
        -------
        Series
            Returns a Series of `Dataset` objects
        """
        try:
            return self.data.Datasets
        except Exception:
            print('Unable to load Datasets successfully. Returning empty series.')
            return pd.Series()

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
        self._raw_data = None
        self._data = pd.DataFrame()
        self.container = Container(self.attributes["container"]["id"], attributes=self.attributes["container"],
                                   connection=connection)

    @property
    def raw_data(self):
        if not self._raw_data:
            # Get all raw data
            self._raw_data = self.connection.dataset(data_id=self.id, key="*")
        return self._raw_data

    @property
    def data(self, key="*"):
        if self._data.empty:
            # Get all data initially (think about lazy loading in the future)
            try:
                self._data = pd.DataFrame(self.raw_data)
            except:
                raise RuntimeError("Failed to cast data as DataFrame. Try using raw_data property instead.")
            self._data.columns = [x.upper() for x in self._data.columns]
        if key == "*":
            return self._data
        else:
            return self._data[key]

    def cross_ref_aliquots(self):
        # Use the container.aliquots DataFrame as the base
        aliquot_data = deepcopy(self.container.aliquots)
        data_column = []
        indices_without_data = []
        # Print a warning if new column will overwrite existing column
        if "Aliquot Data" in aliquot_data.columns.values.tolist():
            warnings.warn("Column 'Aliquot Data' will be overwritten with data pulled from Dataset.")
        # Look up data for every well index
        for index in aliquot_data.index:
            # Get humanized index
            humanized_index = self.container.container_type.humanize(int(index))
            if humanized_index in self.data:
                # Use humanized index to get data for that well
                data_point = self.data.loc[0, humanized_index]
            else:
                # If no data for that well, use None instead
                data_point = None
                indices_without_data.append(humanized_index)
            # Append data point to list
            data_column.append(data_point)
        # Print a list of well indices that do not have corresponding data keys
        if len(indices_without_data) > 0:
            warnings.warn("The following indices were not found as data keys: %s" % ", ".join(indices_without_data))
        # Add these data as a column to the DataFrame
        aliquot_data["Aliquot Data"] = data_column

        return aliquot_data

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
            style="height:400px; width:450px" seamless></iframe>""" % \
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
            myRun.Instructions[1]
            myRun.Instructions[1].warps


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
            if len(warp_list) != 0:
                self._warps = pd.DataFrame(x['command'] for x in warp_list)
                self._warps.columns = [x.title() for x in self._warps.columns.tolist()]
                # Rearrange columns to start with `Name`
                if "Name" in self._warps.columns:
                    col_names = ["Name"] + [col for col in self._warps.columns if col != "Name"]
                    self._warps = self._warps[col_names]
                self._warps.insert(1, "WarpId", [x["id"] for x in warp_list])
                self._warps.insert(2, "Completed", [x["reported_completed_at"] for x in warp_list])
                self._warps.insert(3, "Started", [x["reported_started_at"] for x in warp_list])
            else:
                warnings.warn("There are no warps associated with this instruction. Please contact "
                              "Transcriptic for assistance.")
        return self._warps

    def monitoring(self, data_type='pressure', grouping=None):
        """
        View monitoring data of a given instruction

        Parameters
        ----------
        data_type: Optional[str]
            Monitoring data type, defaults to 'pressure'
        grouping: Optional[str]
            Determines whether the values will be grouped, defaults to None. E.g. "5:ms"

        Returns
        -------
        DataFrame
            Returns a pandas dataframe of the monitoring data
        """
        response = self.connection.monitoring_data(
            instruction_id=self.id,
            data_type=data_type,
            grouping=grouping
        )
        return pd.DataFrame(response['results'])

    def _repr_html_(self):
        return """<iframe src="%s" frameborder="0" allowtransparency="true" \
            style="width:450px" seamless></iframe>""" % \
               self.connection.get_route('view_instruction', run_id=self.attributes["run_id"],
                                         project_id=self.attributes["project_id"], instruction_id=self.id)


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
        DataFrame of aliquots present in the container. DataFrame index
        now corresponds to the Well Index.
    container_type: autoprotocol.container_type.ContainerType
        Autoprotocol ContainerType object with many useful container type
        information and functions.
    cover: str
        Cover type of container
    storage: str
        Storage condition of container

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
        self.cover = self.attributes["cover"]
        self.name = self.attributes["label"]
        self.storage = self.attributes["storage_condition"]
        self.well_map = {aliquot["well_idx"]: aliquot["name"]
                         for aliquot in self.attributes["aliquots"]}
        self.container_type = self._parse_container_type()
        self._aliquots = pd.DataFrame()

    def _parse_container_type(self):
        """Helper function for parsing container string into container object"""
        from autoprotocol.container_type import _CONTAINER_TYPES
        container_type = self.attributes["container_type"]

        # Return the corresponding AP-Py container object for now. In the future, consider merging
        # the current and future dictionary when instantiating container_type
        try:
            return _CONTAINER_TYPES[container_type["shortname"]]
        except KeyError:
            warnings.warn("ContainerType given is not supported yet in AP-Py")
            return None

    @property
    def aliquots(self):
        """
        Return a DataFrame of aliquots in the container, along with aliquot
        name, volume, and properties. Row index for the DataFrame corresponds
        to the well index of the aliquot.

        """
        if self._aliquots.empty:
            aliquot_list = self.attributes["aliquots"]
            self._aliquots = pd.DataFrame(sorted([dict({'Well Index': x['well_idx'], 'Name': x['name'], 'Id': x['id'],
                                                 'Volume': Unit(float(x['volume_ul']), 'microliter')}, **x['properties'])
                                           for x in aliquot_list], key=itemgetter('Well Index')))
            indices = self._aliquots.pop('Well Index')
            self._aliquots.set_index(indices, inplace=True)
        return self._aliquots

    def __repr__(self):
        """
        Return a string representation of a Container using the specified name.
        (ex. Container('my_plate'))

        """
        return "Container(%s)" % (str(self.name))

